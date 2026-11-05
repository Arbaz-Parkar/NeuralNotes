"""Create workspace-scoped chunks with pgvector embeddings.

Revision ID: 20261105_0002
Revises: 20261105_0001
Create Date: 2026-11-05
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR

revision = "20261105_0002"
down_revision = "20261105_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "chunks",
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.String(length=255), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("strategy", sa.String(length=32), nullable=False),
        sa.Column(
            "section_path",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("embedding_model", sa.String(length=255), nullable=False),
        sa.Column("embedding", VECTOR(384), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("page_number >= 1", name="ck_chunks_page_number"),
        sa.CheckConstraint("chunk_index >= 0", name="ck_chunks_chunk_index"),
        sa.CheckConstraint("start_char >= 0", name="ck_chunks_start_char"),
        sa.CheckConstraint("end_char > start_char", name="ck_chunks_character_range"),
        sa.CheckConstraint("token_count > 0", name="ck_chunks_token_count"),
        sa.CheckConstraint(
            "strategy IN ('fixed_size', 'recursive', 'sentence_window')",
            name="ck_chunks_strategy",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "document_id"],
            ["documents.workspace_id", "documents.id"],
            name="fk_chunks_document",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("workspace_id", "document_id", "id", name="pk_chunks"),
    )
    op.create_index(
        "ix_chunks_workspace_document",
        "chunks",
        ["workspace_id", "document_id"],
    )
    op.create_index(
        "ix_chunks_embedding_cosine",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_table("chunks")
