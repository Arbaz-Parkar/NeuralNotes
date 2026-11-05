"""Initial workspace and document persistence models."""

from datetime import date, datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text as sql_text

from neuralnotes.db.base import Base


class Workspace(Base):
    """Tenant boundary for documents and their future chunks."""

    __tablename__ = "workspaces"
    __table_args__ = (PrimaryKeyConstraint("id", name="pk_workspaces"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Document(Base):
    """Source and license metadata for one workspace-scoped document."""

    __tablename__ = "documents"
    __table_args__ = (
        PrimaryKeyConstraint("workspace_id", "id", name="pk_documents"),
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_documents_workspace",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "workspace_id",
            "source_hash",
            name="uq_documents_workspace_source_hash",
        ),
        CheckConstraint(
            "length(source_hash) = 64",
            name="ck_documents_source_hash_length",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed')",
            name="ck_documents_status",
        ),
    )

    workspace_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)
    pdf_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(Text)
    year: Mapped[int | None]
    license_name: Mapped[str | None] = mapped_column(String(100))
    license_url: Mapped[str | None] = mapped_column(Text)
    license_evidence_url: Mapped[str | None] = mapped_column(Text)
    license_verified_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        server_default=sql_text("'pending'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Chunk(Base):
    """Workspace-scoped source passage and its embedding vector."""

    __tablename__ = "chunks"
    __table_args__ = (
        PrimaryKeyConstraint("workspace_id", "document_id", "id", name="pk_chunks"),
        ForeignKeyConstraint(
            ["workspace_id", "document_id"],
            ["documents.workspace_id", "documents.id"],
            name="fk_chunks_document",
            ondelete="CASCADE",
        ),
        CheckConstraint("page_number >= 1", name="ck_chunks_page_number"),
        CheckConstraint("chunk_index >= 0", name="ck_chunks_chunk_index"),
        CheckConstraint("start_char >= 0", name="ck_chunks_start_char"),
        CheckConstraint("end_char > start_char", name="ck_chunks_character_range"),
        CheckConstraint("token_count > 0", name="ck_chunks_token_count"),
        CheckConstraint(
            "strategy IN ('fixed_size', 'recursive', 'sentence_window')",
            name="ck_chunks_strategy",
        ),
        Index("ix_chunks_workspace_document", "workspace_id", "document_id"),
        Index(
            "ix_chunks_embedding_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    workspace_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    document_id: Mapped[str] = mapped_column(String(255), nullable=False)
    id: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_char: Mapped[int] = mapped_column(Integer, nullable=False)
    end_char: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    section_path: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list, server_default=sql_text("'[]'")
    )
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(VECTOR(384), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
