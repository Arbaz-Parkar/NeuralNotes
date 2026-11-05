"""Initial workspace and document persistence models."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

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
        String(16), nullable=False, default="pending", server_default=text("'pending'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
