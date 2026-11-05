"""Persist prepared documents and their embedded chunks in one transaction."""

from datetime import date
from hashlib import file_digest
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from neuralnotes.db.models import Chunk as ChunkRecord
from neuralnotes.db.models import Document
from neuralnotes.embeddings.sentence_transformer import DEFAULT_EMBEDDING_MODEL
from neuralnotes.ingestion.pipeline import PreparedDocument


def persist_prepared_document(
    session: Session,
    prepared: PreparedDocument,
    *,
    workspace_id: UUID,
    mime_type: str,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    source_url: str | None = None,
    pdf_url: str | None = None,
    year: int | None = None,
    license_name: str | None = None,
    license_url: str | None = None,
    license_evidence_url: str | None = None,
    license_verified_on: date | None = None,
) -> Document:
    """Add a prepared document and its chunks to the caller's transaction.

    The caller controls commit and rollback, for example with
    ``with session_factory.begin() as session``. Repeating an import with the
    same document id and file content replaces its chunk rows without
    duplicating them.
    """
    if not prepared.document_id.strip():
        raise ValueError("Prepared document id must not be empty.")
    if not mime_type.strip():
        raise ValueError("mime_type must not be empty.")
    if not embedding_model.strip():
        raise ValueError("embedding_model must not be empty.")
    if not prepared.chunks:
        raise ValueError("Prepared document must contain at least one chunk.")

    chunk_ids = tuple(item.chunk.chunk_id for item in prepared.chunks)
    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError("Prepared document contains duplicate chunk ids.")

    vector_dimension = ChunkRecord.__table__.columns["embedding"].type.dim
    chunk_records: list[ChunkRecord] = []
    for item in prepared.chunks:
        chunk = item.chunk
        if chunk.document_id != prepared.document_id:
            raise ValueError("Every chunk must belong to the prepared document.")
        if len(item.embedding) != vector_dimension:
            raise ValueError(
                f"Chunk embeddings must contain {vector_dimension} values."
            )
        chunk_records.append(
            ChunkRecord(
                workspace_id=workspace_id,
                document_id=prepared.document_id,
                id=chunk.chunk_id,
                text=chunk.text,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                token_count=chunk.token_count,
                strategy=chunk.strategy,
                section_path=list(chunk.section_path),
                embedding_model=embedding_model,
                embedding=list(item.embedding),
            )
        )

    source_hash = _hash_file(prepared.source_path)
    existing_source = session.scalar(
        select(Document).where(
            Document.workspace_id == workspace_id,
            Document.source_hash == source_hash,
        )
    )
    if existing_source is not None and existing_source.id != prepared.document_id:
        raise ValueError(
            "This source file is already stored under a different document id."
        )

    document = session.get(Document, (workspace_id, prepared.document_id))
    if document is None:
        document = Document(
            workspace_id=workspace_id,
            id=prepared.document_id,
            source_hash=source_hash,
            mime_type=mime_type,
        )
        session.add(document)
    else:
        document.source_hash = source_hash
        document.mime_type = mime_type
        session.execute(
            delete(ChunkRecord).where(
                ChunkRecord.workspace_id == workspace_id,
                ChunkRecord.document_id == prepared.document_id,
            )
        )

    document.source_name = prepared.source_path.name
    document.source_url = source_url
    document.pdf_url = pdf_url
    document.title = prepared.title
    document.author = prepared.author
    document.year = year
    document.license_name = license_name
    document.license_url = license_url
    document.license_evidence_url = license_evidence_url
    document.license_verified_on = license_verified_on
    document.status = "ready"
    session.flush()
    session.add_all(chunk_records)
    session.flush()
    return document


def _hash_file(path: Path) -> str:
    with path.open("rb") as source:
        return file_digest(source, "sha256").hexdigest()
