"""Tests for workspace-scoped SQLAlchemy document metadata."""

from neuralnotes.db import Document, Workspace


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
