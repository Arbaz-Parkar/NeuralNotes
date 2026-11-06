"""Tests for manifest-based batch ingestion."""

from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from neuralnotes.chunking import Chunk as SourceChunk
from neuralnotes.db import Base, Chunk, Document, Workspace
from neuralnotes.downloader import Paper
from neuralnotes.ingestion import cli
from neuralnotes.ingestion.pipeline import EmbeddedChunk, PreparedDocument
from neuralnotes.settings import Settings

WORKSPACE_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


class FakePipeline:
    def __init__(self) -> None:
        self.document_ids: list[str] = []

    def prepare(self, source_path: Path, *, document_id: str) -> PreparedDocument:
        self.document_ids.append(document_id)
        chunk = SourceChunk(
            chunk_id=(document_id.encode("utf-8").hex() + "0" * 64)[:64],
            document_id=document_id,
            text="sample passage",
            page_number=1,
            chunk_index=0,
            start_char=0,
            end_char=15,
            token_count=2,
            strategy="fixed_size",
        )
        vector = (0.6, 0.8) + (0.0,) * 382
        return PreparedDocument(
            document_id=document_id,
            source_path=source_path,
            title=f"Title for {document_id}",
            author="Researcher",
            page_count=1,
            chunks=(EmbeddedChunk(chunk=chunk, embedding=vector),),
        )


def _paper(paper_id: str, year: int) -> Paper:
    return Paper(
        anthology_id=paper_id,
        title=f"Title for {paper_id}",
        year=year,
        landing_page_url=f"https://aclanthology.org/{paper_id}/",
        pdf_url=f"https://aclanthology.org/{paper_id}.pdf",
        license="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        license_evidence_url=f"https://aclanthology.org/{paper_id}/",
        license_verified_on="2026-11-02",
    )


def test_ingest_manifest_reuses_pipeline_and_commits_each_paper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    papers = (
        _paper("2020.emnlp-main.550", 2020),
        _paper("2021.acl-long.1", 2021),
        _paper("2022.findings-acl.2", 2022),
    )
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    for paper in (papers[0], papers[2]):
        (pdf_dir / f"{paper.anthology_id}.pdf").write_bytes(
            paper.anthology_id.encode("utf-8")
        )

    pipeline = FakePipeline()
    monkeypatch.setattr(cli, "load_manifest", lambda _path: list(papers))
    monkeypatch.setattr(cli, "_build_pipeline", lambda: pipeline)

    database_path = tmp_path / "batch.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    schema_engine = create_engine(database_url)
    Base.metadata.create_all(schema_engine)
    schema_engine.dispose()

    result = cli.ingest_manifest(
        paper_ids=tuple(paper.anthology_id for paper in papers),
        manifest_path=tmp_path / "manifest.json",
        pdf_dir=pdf_dir,
        workspace_id=WORKSPACE_ID,
        workspace_name="Batch workspace",
        settings=Settings(database_url=database_url),
    )

    assert [item.document_id for item in result.ingested] == [
        papers[0].anthology_id,
        papers[2].anthology_id,
    ]
    assert [failure.document_id for failure in result.failures] == [
        papers[1].anthology_id
    ]
    assert "Local PDF not found" in result.failures[0].error
    assert pipeline.document_ids == [papers[0].anthology_id, papers[2].anthology_id]

    verification_engine = create_engine(database_url)
    try:
        with Session(verification_engine) as session:
            document_count = session.scalar(select(func.count()).select_from(Document))
            chunk_count = session.scalar(select(func.count()).select_from(Chunk))
            workspace = session.get(Workspace, WORKSPACE_ID)

        assert document_count == 2
        assert chunk_count == 2
        assert workspace is not None
        assert workspace.name == "Batch workspace"
    finally:
        verification_engine.dispose()


@pytest.mark.parametrize(
    ("paper_ids", "message"),
    [
        ((), "At least one paper id"),
        (("missing-paper",), "not present in the verified manifest"),
        (("2020.emnlp-main.550", "2020.emnlp-main.550"), "duplicates"),
    ],
)
def test_ingest_manifest_validates_selected_ids_before_database_access(
    paper_ids: tuple[str, ...],
    message: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli,
        "load_manifest",
        lambda _path: [_paper("2020.emnlp-main.550", 2020)],
    )

    with pytest.raises(ValueError, match=message):
        cli.ingest_manifest(
            paper_ids=paper_ids,
            manifest_path=tmp_path / "manifest.json",
        )


def test_cli_returns_failure_when_a_batch_item_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = cli.BatchIngestionResult(
        ingested=(),
        failures=(cli.IngestionFailure(document_id="paper-1", error="missing PDF"),),
    )
    captured: dict[str, object] = {}

    def fail_batch(**kwargs: object) -> cli.BatchIngestionResult:
        captured.update(kwargs)
        return result

    monkeypatch.setattr(cli, "ingest_manifest", fail_batch)
    monkeypatch.setattr(cli, "configure_logging", lambda: None)

    assert cli.main(["--all"]) == 1
    assert captured["paper_ids"] is None
