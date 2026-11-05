"""Tests for saving prepared ingestion results as SQLAlchemy records."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from neuralnotes.chunking import Chunk as SourceChunk
from neuralnotes.db import Base, Chunk, Document, Workspace
from neuralnotes.db.persistence import persist_prepared_document
from neuralnotes.ingestion.pipeline import EmbeddedChunk, PreparedDocument


def _prepared_document(source_path) -> PreparedDocument:
    chunk = SourceChunk(
        chunk_id="a" * 64,
        document_id="paper-1",
        text="alpha",
        page_number=1,
        chunk_index=0,
        start_char=0,
        end_char=5,
        token_count=1,
        strategy="fixed_size",
        section_path=("Introduction",),
    )
    embedding = (0.6, 0.8) + (0.0,) * 382
    return PreparedDocument(
        document_id="paper-1",
        source_path=source_path,
        title="Example paper",
        author="Researcher",
        page_count=1,
        chunks=(EmbeddedChunk(chunk=chunk, embedding=embedding),),
    )


def _create_sqlite_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def test_persist_prepared_document_stores_document_and_chunk_metadata(
    tmp_path,
) -> None:
    source_path = tmp_path / "paper.pdf"
    source_path.write_bytes(b"example PDF source")
    prepared = _prepared_document(source_path)
    workspace_id = uuid4()
    engine = _create_sqlite_engine()

    try:
        with Session(engine) as session, session.begin():
            session.add(Workspace(id=workspace_id, name="Research"))
            document = persist_prepared_document(
                session,
                prepared,
                workspace_id=workspace_id,
                mime_type="application/pdf",
                source_url="https://example.test/paper",
                pdf_url="https://example.test/paper.pdf",
                license_name="CC-BY-4.0",
                license_url="https://creativecommons.org/licenses/by/4.0/",
            )

            assert document.status == "ready"

        with Session(engine) as session:
            document = session.get(Document, (workspace_id, "paper-1"))
            chunks = session.scalars(select(Chunk)).all()

        assert document is not None
        assert document.source_name == "paper.pdf"
        assert document.title == "Example paper"
        assert document.mime_type == "application/pdf"
        assert document.source_hash
        assert document.license_name == "CC-BY-4.0"
        assert len(chunks) == 1
        assert chunks[0].text == "alpha"
        assert chunks[0].page_number == 1
        assert chunks[0].section_path == ["Introduction"]
        assert len(chunks[0].embedding) == 384
    finally:
        engine.dispose()


def test_persist_prepared_document_replaces_chunks_without_duplicates(
    tmp_path,
) -> None:
    source_path = tmp_path / "paper.pdf"
    source_path.write_bytes(b"example PDF source")
    prepared = _prepared_document(source_path)
    workspace_id = uuid4()
    engine = _create_sqlite_engine()

    try:
        with Session(engine) as session, session.begin():
            session.add(Workspace(id=workspace_id, name="Research"))
            persist_prepared_document(
                session,
                prepared,
                workspace_id=workspace_id,
                mime_type="application/pdf",
            )

        with Session(engine) as session, session.begin():
            persist_prepared_document(
                session,
                prepared,
                workspace_id=workspace_id,
                mime_type="application/pdf",
            )

        with Session(engine) as session:
            document_count = session.scalar(select(func.count()).select_from(Document))
            chunk_count = session.scalar(select(func.count()).select_from(Chunk))

        assert document_count == 1
        assert chunk_count == 1
    finally:
        engine.dispose()


def test_persist_prepared_document_rejects_wrong_embedding_dimension(
    tmp_path,
) -> None:
    source_path = tmp_path / "paper.pdf"
    source_path.write_bytes(b"example PDF source")
    prepared = _prepared_document(source_path)
    wrong_vector = EmbeddedChunk(
        chunk=prepared.chunks[0].chunk,
        embedding=(0.6, 0.8),
    )
    prepared = PreparedDocument(
        document_id=prepared.document_id,
        source_path=prepared.source_path,
        title=prepared.title,
        author=prepared.author,
        page_count=prepared.page_count,
        chunks=(wrong_vector,),
    )
    engine = _create_sqlite_engine()

    try:
        with Session(engine) as session:
            with pytest.raises(ValueError, match="384 values"):
                persist_prepared_document(
                    session,
                    prepared,
                    workspace_id=uuid4(),
                    mime_type="application/pdf",
                )
    finally:
        engine.dispose()
