"""Tests for workspace-scoped SQLAlchemy document metadata."""

from neuralnotes.db import Chunk, Document, Workspace


def test_document_primary_key_is_scoped_to_workspace() -> None:
    assert tuple(Document.__table__.primary_key.columns.keys()) == (
        "workspace_id",
        "id",
    )


def test_document_schema_keeps_source_and_license_evidence() -> None:
    columns = Document.__table__.columns

    assert "source_hash" in columns
    assert "source_url" in columns
    assert "license_name" in columns
    assert "license_url" in columns
    assert "license_evidence_url" in columns
    assert "license_verified_on" in columns


def test_workspace_table_has_a_uuid_key_and_name() -> None:
    columns = Workspace.__table__.columns

    assert columns["id"].primary_key
    assert columns["id"].type.__class__.__name__ == "Uuid"
    assert "name" in columns


def test_chunk_key_and_document_reference_include_workspace() -> None:
    assert tuple(Chunk.__table__.primary_key.columns.keys()) == (
        "workspace_id",
        "document_id",
        "id",
    )

    foreign_key = next(iter(Chunk.__table__.foreign_key_constraints))
    assert [element.target_fullname for element in foreign_key.elements] == [
        "documents.workspace_id",
        "documents.id",
    ]


def test_chunk_schema_keeps_source_positions_and_embedding_details() -> None:
    columns = Chunk.__table__.columns

    assert {
        "text",
        "page_number",
        "chunk_index",
        "start_char",
        "end_char",
        "token_count",
        "strategy",
        "section_path",
        "embedding_model",
        "embedding",
    }.issubset(columns.keys())
    assert columns["embedding"].type.dim == 384


def test_chunk_embedding_index_uses_cosine_hnsw() -> None:
    index = next(
        index
        for index in Chunk.__table__.indexes
        if index.name == "ix_chunks_embedding_cosine"
    )

    assert index.dialect_options["postgresql"]["using"] == "hnsw"
    assert index.dialect_options["postgresql"]["ops"] == {
        "embedding": "vector_cosine_ops"
    }
