"""Create workspace and document tables.

Revision ID: 20261105_0001
Revises:
Create Date: 2026-11-05
"""

import sqlalchemy as sa
from alembic import op

revision = "20261105_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workspaces"),
    )
    op.create_table(
        "documents",
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("license_name", sa.String(length=100), nullable=True),
        sa.Column("license_url", sa.Text(), nullable=True),
        sa.Column("license_evidence_url", sa.Text(), nullable=True),
        sa.Column("license_verified_on", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(source_hash) = 64",
            name="ck_documents_source_hash_length",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed')",
            name="ck_documents_status",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_documents_workspace",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("workspace_id", "id", name="pk_documents"),
        sa.UniqueConstraint(
            "workspace_id",
            "source_hash",
            name="uq_documents_workspace_source_hash",
        ),
    )


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("workspaces")
