"""Tests for the HTTP API."""

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from neuralnotes.api import app, get_db_session
from neuralnotes.db import Base, Document, Workspace
from neuralnotes.db import Chunk as ChunkRecord


def test_health_endpoint_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_endpoint_returns_only_requested_workspace_results(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "search.sqlite3"
    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)
    first_workspace_id = uuid4()
    second_workspace_id = uuid4()

    try:
        with Session(engine) as session, session.begin():
            session.add_all(
                (
                    Workspace(id=first_workspace_id, name="First"),
                    Workspace(id=second_workspace_id, name="Second"),
                )
            )
            _add_search_chunk(
                session,
                workspace_id=first_workspace_id,
                document_id="retrieval-paper",
                chunk_id="a" * 64,
                text="Dense passage retrieval finds evidence.",
            )
            _add_search_chunk(
                session,
                workspace_id=second_workspace_id,
                document_id="biology-paper",
                chunk_id="b" * 64,
                text="Biology evidence discusses cells.",
            )

        def override_session():
            with Session(engine) as session:
                yield session

        app.dependency_overrides[get_db_session] = override_session
        with TestClient(app) as client:
            response = client.post(
                "/v1/search",
                json={
                    "workspace_id": str(first_workspace_id),
                    "query": "evidence",
                    "top_k": 3,
                },
            )

        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["chunk_id"] == "a" * 64
        assert results[0]["document_id"] == "retrieval-paper"
        assert results[0]["text"] == "Dense passage retrieval finds evidence."
        assert results[0]["page_number"] == 1
        assert results[0]["start_char"] == 0
        assert results[0]["end_char"] == len("Dense passage retrieval finds evidence.")
        assert results[0]["score"] > 0
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        engine.dispose()


def test_search_endpoint_rejects_blank_query() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/search",
            json={"workspace_id": str(uuid4()), "query": "   "},
        )

    assert response.status_code == 422


def _add_search_chunk(
    session: Session,
    *,
    workspace_id,
    document_id: str,
    chunk_id: str,
    text: str,
) -> None:
    session.add(
        Document(
            workspace_id=workspace_id,
            id=document_id,
            source_hash=chunk_id,
            mime_type="text/plain",
            status="ready",
        )
    )
    session.flush()
    session.add(
        ChunkRecord(
            workspace_id=workspace_id,
            document_id=document_id,
            id=chunk_id,
            text=text,
            page_number=1,
            chunk_index=0,
            start_char=0,
            end_char=len(text),
            token_count=len(text.split()),
            strategy="fixed_size",
            section_path=[],
            embedding_model="test-model",
            embedding=[0.0] * 384,
        )
    )
