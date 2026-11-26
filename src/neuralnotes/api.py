"""HTTP API application, health check, and workspace-scoped search."""

import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session, sessionmaker

from neuralnotes.database import (
    create_database_engine,
    create_database_session_factory,
)
from neuralnotes.db.retrieval import build_workspace_bm25_index
from neuralnotes.generation import (
    GroundedAnswer,
    OllamaAnswerGenerator,
    OllamaGenerationError,
    RetrievedPassage,
    generate_grounded_answer,
)
from neuralnotes.generation.prompts import ACTIVE_ANSWER_PROMPT_VERSION
from neuralnotes.logging_config import configure_logging
from neuralnotes.settings import Settings
from neuralnotes.telemetry import generation_summary, tracer

settings = Settings()
logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    """Input for a lexical search within one workspace."""

    workspace_id: UUID
    query: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=5, ge=1, le=50)
    min_score: float | None = Field(default=None, ge=0.0)

    @field_validator("query")
    @classmethod
    def require_non_whitespace_query(cls, value: str) -> str:
        """Reject queries that contain no searchable characters."""
        query = value.strip()
        if not query:
            raise ValueError("query must contain at least one non-whitespace character")
        return query


class SearchResult(BaseModel):
    """One passage returned by workspace-scoped lexical search."""

    chunk_id: str
    document_id: str
    text: str
    page_number: int
    start_char: int
    end_char: int
    score: float


class SearchResponse(BaseModel):
    """Ranked passage results for a search request."""

    results: list[SearchResult]
    abstained: bool
    min_score: float | None


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Create the shared database pool and release it at application shutdown."""
    configure_logging(settings.log_level)
    engine = create_database_engine(settings)
    application.state.session_factory = create_database_session_factory(engine)
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.middleware("http")
async def log_request(request: Request, call_next):
    """Attach a request id and log request outcome without logging its body."""
    request_id = uuid4()
    started_at = perf_counter()
    with tracer.start_as_current_span("http.request") as span:
        span.set_attribute("http.request.method", request.method)
        span.set_attribute("url.path", request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request failed", extra={"request_id": request_id})
            raise

        duration_ms = (perf_counter() - started_at) * 1_000
        span.set_attribute("http.response.status_code", response.status_code)
        span.set_attribute("request.duration_ms", duration_ms)
        trace_id = format(span.get_span_context().trace_id, "032x")
        response.headers["X-Request-ID"] = str(request_id)
        response.headers["X-Trace-ID"] = trace_id
        logger.info(
            "request completed method=%s path=%s status_code=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={"request_id": request_id},
        )
        return response


def get_db_session(request: Request) -> Iterator[Session]:
    """Yield a request-scoped SQLAlchemy session and close it afterward."""
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}


@app.get("/v1/observability/summary", tags=["observability"])
def observability_summary() -> dict[str, int | float | None]:
    """Return bounded, process-local generation latency and token summaries."""
    return generation_summary()


@app.post("/v1/search", response_model=SearchResponse, tags=["retrieval"])
def search_workspace(
    request: SearchRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> SearchResponse:
    """Return the highest-scoring BM25 passages from the requested workspace."""
    with tracer.start_as_current_span("retrieval") as span:
        index = build_workspace_bm25_index(session, request.workspace_id)
        hits = index.search(request.query, top_k=request.top_k)
        if request.min_score is not None:
            hits = tuple(hit for hit in hits if hit.score >= request.min_score)
        span.set_attribute("retrieval.result_count", len(hits))
    return SearchResponse(
        results=[
            SearchResult(
                chunk_id=hit.chunk.chunk_id,
                document_id=hit.chunk.document_id,
                text=hit.chunk.text,
                page_number=hit.chunk.page_number,
                start_char=hit.chunk.start_char,
                end_char=hit.chunk.end_char,
                score=hit.score,
            )
            for hit in hits
        ],
        abstained=request.min_score is not None and not hits,
        min_score=request.min_score,
    )


@app.post("/v1/answer", response_model=GroundedAnswer, tags=["generation"])
def answer_workspace(
    request: SearchRequest,
    session: Annotated[Session, Depends(get_db_session)],
    response: Response,
) -> GroundedAnswer:
    """Generate a cited answer from workspace-scoped BM25 passages."""
    with tracer.start_as_current_span("retrieval") as span:
        index = build_workspace_bm25_index(session, request.workspace_id)
        hits = index.search(request.query, top_k=request.top_k)
        if request.min_score is not None:
            hits = tuple(hit for hit in hits if hit.score >= request.min_score)
        span.set_attribute("retrieval.result_count", len(hits))

    passages = tuple(
        RetrievedPassage(
            chunk_id=hit.chunk.chunk_id,
            document_id=hit.chunk.document_id,
            text=hit.chunk.text,
            page_number=hit.chunk.page_number,
            start_char=hit.chunk.start_char,
            end_char=hit.chunk.end_char,
        )
        for hit in hits
    )
    generator = OllamaAnswerGenerator(
        model_name=settings.ollama_model,
        base_url=settings.ollama_base_url,
        timeout_seconds=settings.ollama_timeout_seconds,
        max_output_tokens=settings.ollama_max_output_tokens,
    )
    response.headers["X-Prompt-Version"] = ACTIVE_ANSWER_PROMPT_VERSION
    try:
        with tracer.start_as_current_span("generation") as span:
            span.set_attribute("llm.model", settings.ollama_model)
            span.set_attribute("prompt.version", ACTIVE_ANSWER_PROMPT_VERSION)
            answer = generate_grounded_answer(request.query, passages, generator)
            span.set_attribute("answer.abstained", answer.abstained)
            span.set_attribute("answer.claim_count", len(answer.claims))
            return answer
    except OllamaGenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
