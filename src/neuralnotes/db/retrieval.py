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
    records = session.scalars(
        select(ChunkRecord)
        .where(ChunkRecord.workspace_id == workspace_id)
        .order_by(
            ChunkRecord.document_id,
            ChunkRecord.chunk_index,
            ChunkRecord.id,
        )
    ).all()
    chunks = tuple(
        SourceChunk(
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
        for record in records
    )
    return BM25Index(chunks, k1=k1, b=b)
