"""HTTP API application, health check, and workspace-scoped search."""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session, sessionmaker

from neuralnotes.database import (
    create_database_engine,
    create_database_session_factory,
)
from neuralnotes.db.retrieval import build_workspace_bm25_index
from neuralnotes.settings import Settings

settings = Settings()


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
    engine = create_database_engine(settings)
    application.state.session_factory = create_database_session_factory(engine)
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)


def get_db_session(request: Request) -> Iterator[Session]:
    """Yield a request-scoped SQLAlchemy session and close it afterward."""
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}


@app.post("/v1/search", response_model=SearchResponse, tags=["retrieval"])
def search_workspace(
    request: SearchRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> SearchResponse:
    """Return the highest-scoring BM25 passages from the requested workspace."""
    index = build_workspace_bm25_index(session, request.workspace_id)
    hits = index.search(request.query, top_k=request.top_k)
    if request.min_score is not None:
        hits = tuple(hit for hit in hits if hit.score >= request.min_score)
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
