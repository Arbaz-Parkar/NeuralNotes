"""Tests for the one-paper local ingestion command."""

from datetime import date
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from neuralnotes.chunking import Chunk as SourceChunk
from neuralnotes.db import Base, Chunk, Document, Workspace
from neuralnotes.downloader import Paper
from neuralnotes.ingestion import cli
from neuralnotes.ingestion.pipeline import EmbeddedChunk, PreparedDocument
from neuralnotes.settings import Settings

PAPER_ID = "2020.emnlp-main.550"
WORKSPACE_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


class FakePipeline:
    def __init__(self, prepared: PreparedDocument) -> None:
        self.prepared = prepared
        self.received: tuple[Path, str] | None = None

    def prepare(self, source_path: Path, *, document_id: str) -> PreparedDocument:
        self.received = source_path, document_id
        return self.prepared


def _paper() -> Paper:
    return Paper(
        anthology_id=PAPER_ID,
        title="Example paper",
        year=2020,
        landing_page_url=f"https://aclanthology.org/{PAPER_ID}/",
        pdf_url=f"https://aclanthology.org/{PAPER_ID}.pdf",
        license="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        license_evidence_url=f"https://aclanthology.org/{PAPER_ID}/",
        license_verified_on="2026-11-02",
    )


def _prepared_document(source_path: Path) -> PreparedDocument:
    chunk = SourceChunk(
        chunk_id="a" * 64,
        document_id=PAPER_ID,
        text="alpha",
        page_number=1,
        chunk_index=0,
        start_char=0,
        end_char=5,
        token_count=1,
        strategy="fixed_size",
        section_path=(),
    )
    vector = (0.6, 0.8) + (0.0,) * 382
    return PreparedDocument(
        document_id=PAPER_ID,
        source_path=source_path,
        title="Example paper",
        author="Researcher",
        page_count=1,
        chunks=(EmbeddedChunk(chunk=chunk, embedding=vector),),
    )


def test_ingest_paper_persists_license_metadata_and_embedded_chunks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    source_path = pdf_dir / f"{PAPER_ID}.pdf"
    source_path.write_bytes(b"example PDF bytes")
    prepared = _prepared_document(source_path)
    pipeline = FakePipeline(prepared)
    monkeypatch.setattr(cli, "load_manifest", lambda _path: [_paper()])
    monkeypatch.setattr(cli, "_build_pipeline", lambda: pipeline)

    database_path = tmp_path / "neuralnotes.sqlite"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    schema_engine = create_engine(database_url)
    Base.metadata.create_all(schema_engine)
    schema_engine.dispose()

    result = cli.ingest_paper(
        PAPER_ID,
        manifest_path=tmp_path / "manifest.json",
        pdf_dir=pdf_dir,
        workspace_id=WORKSPACE_ID,
        workspace_name="Test workspace",
        settings=Settings(database_url=database_url),
    )

    assert pipeline.received == (source_path, PAPER_ID)
    assert result.document_id == PAPER_ID
    assert result.workspace_id == WORKSPACE_ID
    assert result.page_count == 1
    assert result.chunk_count == 1

    verification_engine = create_engine(database_url)
    try:
        with Session(verification_engine) as session:
            workspace = session.get(Workspace, WORKSPACE_ID)
            document = session.get(Document, (WORKSPACE_ID, PAPER_ID))
            chunks = session.scalars(select(Chunk)).all()

        assert workspace is not None
        assert workspace.name == "Test workspace"
        assert document is not None
        assert document.status == "ready"
        assert document.license_name == "CC-BY-4.0"
        assert document.license_verified_on == date(2026, 11, 2)
        assert len(chunks) == 1
        assert chunks[0].text == "alpha"
        assert len(chunks[0].embedding) == 384
    finally:
        verification_engine.dispose()


def test_ingest_paper_rejects_id_missing_from_verified_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "load_manifest", lambda _path: [_paper()])

    with pytest.raises(ValueError, match="not present in the verified manifest"):
        cli.ingest_paper("unknown-paper", manifest_path=tmp_path / "manifest.json")


def test_ingest_paper_requires_downloaded_pdf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "load_manifest", lambda _path: [_paper()])

    with pytest.raises(FileNotFoundError, match="Run neuralnotes.downloader first"):
        cli.ingest_paper(PAPER_ID, pdf_dir=tmp_path)


def test_cli_returns_nonzero_and_logs_on_ingestion_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_ingestion(*_args: object, **_kwargs: object) -> None:
        raise ValueError("test failure")

    monkeypatch.setattr(cli, "ingest_paper", fail_ingestion)
    monkeypatch.setattr(cli, "configure_logging", lambda: None)

    assert cli.main(["--paper-id", PAPER_ID]) == 1
    assert "Ingestion failed for paper" in caplog.text
