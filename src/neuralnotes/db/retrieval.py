"""Database adapters for workspace-scoped retrieval indexes."""

from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from neuralnotes.chunking import Chunk as SourceChunk
from neuralnotes.chunking import ChunkStrategy
from neuralnotes.db.models import Chunk as ChunkRecord
from neuralnotes.retrieval.bm25 import BM25Index


def build_workspace_bm25_index(
    session: Session,
    workspace_id: UUID,
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> BM25Index:
    """Build an in-memory BM25 snapshot from one workspace's stored chunks.

    The caller should rebuild the index after that workspace's documents change.
    Only chunk rows matching ``workspace_id`` are loaded.
    """
    return BM25Index(load_workspace_chunks(session, workspace_id), k1=k1, b=b)


def load_workspace_chunks(
    session: Session, workspace_id: UUID
) -> tuple[SourceChunk, ...]:
    """Load source-aware chunks belonging only to one workspace."""
    records = session.scalars(
        select(ChunkRecord)
        .where(ChunkRecord.workspace_id == workspace_id)
        .order_by(
            ChunkRecord.document_id,
            ChunkRecord.chunk_index,
            ChunkRecord.id,
        )
    ).all()
    return tuple(_to_source_chunk(record) for record in records)


def load_workspace_chunk_embeddings(
    session: Session, workspace_id: UUID
) -> tuple[tuple[SourceChunk, tuple[float, ...]], ...]:
    """Load workspace chunks paired with their persisted embeddings."""
    records = session.scalars(
        select(ChunkRecord)
        .where(ChunkRecord.workspace_id == workspace_id)
        .order_by(
            ChunkRecord.document_id,
            ChunkRecord.chunk_index,
            ChunkRecord.id,
        )
    ).all()
    return tuple(
        (_to_source_chunk(record), tuple(record.embedding)) for record in records
    )


def get_workspace_embedding_model(session: Session, workspace_id: UUID) -> str | None:
    """Return the single embedding model configured for a workspace."""
    model_names = session.scalars(
        select(ChunkRecord.embedding_model)
        .where(ChunkRecord.workspace_id == workspace_id)
        .distinct()
    ).all()
    if len(model_names) > 1:
        raise ValueError(
            "Dense retrieval requires all workspace chunks to use one embedding model."
        )
    return model_names[0] if model_names else None


def _to_source_chunk(record: ChunkRecord) -> SourceChunk:
    return SourceChunk(
        chunk_id=record.id,
        document_id=record.document_id,
        text=record.text,
        page_number=record.page_number,
        chunk_index=record.chunk_index,
        start_char=record.start_char,
        end_char=record.end_char,
        token_count=record.token_count,
        strategy=cast(ChunkStrategy, record.strategy),
        section_path=tuple(record.section_path),
    )
