"""Tests for loading a workspace-scoped BM25 index from SQLAlchemy."""

from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from neuralnotes.db import Base, Document, Workspace
from neuralnotes.db import Chunk as ChunkRecord
from neuralnotes.db.retrieval import build_workspace_bm25_index, load_workspace_chunks


def _add_document_chunk(
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


def test_workspace_bm25_index_excludes_other_workspaces() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
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
            _add_document_chunk(
                session,
                workspace_id=first_workspace_id,
                document_id="paper-a",
                chunk_id="a" * 64,
                text="neural retrieval evidence",
            )
            _add_document_chunk(
                session,
                workspace_id=second_workspace_id,
                document_id="paper-b",
                chunk_id="b" * 64,
                text="unrelated biology evidence",
            )

        with Session(engine) as session:
            first_index = build_workspace_bm25_index(session, first_workspace_id)
            second_index = build_workspace_bm25_index(session, second_workspace_id)
            first_chunks = load_workspace_chunks(session, first_workspace_id)

        assert first_index.document_count == 1
        assert [hit.chunk.document_id for hit in first_index.search("neural")] == [
            "paper-a"
        ]
        assert first_index.search("biology") == ()
        assert len(first_chunks) == 1
        assert first_chunks[0].document_id == "paper-a"
        assert [hit.chunk.document_id for hit in second_index.search("biology")] == [
            "paper-b"
        ]
    finally:
        engine.dispose()


def test_workspace_bm25_index_handles_workspace_with_no_chunks() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    workspace_id = uuid4()

    try:
        with Session(engine) as session, session.begin():
            session.add(Workspace(id=workspace_id, name="Empty"))

        with Session(engine) as session:
            index = build_workspace_bm25_index(session, workspace_id)

        assert index.document_count == 0
        assert index.search("anything") == ()
    finally:
        engine.dispose()
