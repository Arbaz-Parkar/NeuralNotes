"""Tests for workspace-level ingestion statistics and report rendering."""

from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from neuralnotes.db import Base, Chunk, Document, Workspace
from neuralnotes.ingestion.stats import (
    collect_ingestion_statistics,
    render_statistics_markdown,
)


def test_statistics_report_counts_chunks_by_strategy_and_token_distribution(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "statistics.sqlite3"
    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)
    workspace_id = uuid4()
    chunk_data = (
        ("fixed_size", 4),
        ("fixed_size", 8),
        ("recursive", 12),
        ("sentence_window", 20),
    )

    try:
        with Session(engine) as session, session.begin():
            session.add(Workspace(id=workspace_id, name="Statistics test"))
            for index, (strategy, token_count) in enumerate(chunk_data):
                document_id = f"paper-{index}"
                chunk_id = f"{index + 1:064d}"
                session.add(
                    Document(
                        workspace_id=workspace_id,
                        id=document_id,
                        source_hash=chunk_id,
                        mime_type="text/plain",
                        status="ready",
                    )
                )
                session.flush()
                text = " ".join(f"token{token}" for token in range(token_count))
                session.add(
                    Chunk(
                        workspace_id=workspace_id,
                        document_id=document_id,
                        id=chunk_id,
                        text=text,
                        page_number=1,
                        chunk_index=0,
                        start_char=0,
                        end_char=len(text),
                        token_count=token_count,
                        strategy=strategy,
                        section_path=[],
                        embedding_model="test-model",
                        embedding=[0.0] * 384,
                    )
                )

        with Session(engine) as session:
            statistics = collect_ingestion_statistics(session, workspace_id)

        assert statistics.ready_document_count == 4
        assert statistics.chunk_count == 4
        assert statistics.chunks_by_strategy == (
            ("fixed_size", 2),
            ("recursive", 1),
            ("sentence_window", 1),
        )
        assert statistics.token_distribution.minimum == 4
        assert statistics.token_distribution.median == 10.0
        assert statistics.token_distribution.percentile_95 == 20
        assert statistics.token_distribution.mean == 11.0
        assert statistics.token_distribution.maximum == 20

        report = render_statistics_markdown(statistics)
        assert "Ready documents: 4" in report
        assert "| `fixed_size` | 2 |" in report
        assert "95th percentile: 20" in report
    finally:
        engine.dispose()


def test_statistics_report_handles_empty_workspace(tmp_path: Path) -> None:
    database_path = tmp_path / "empty-statistics.sqlite3"
    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)
    workspace_id = uuid4()

    try:
        with Session(engine) as session, session.begin():
            session.add(Workspace(id=workspace_id, name="Empty"))

        with Session(engine) as session:
            statistics = collect_ingestion_statistics(session, workspace_id)

        assert statistics.ready_document_count == 0
        assert statistics.chunk_count == 0
        assert statistics.token_distribution.minimum is None
        assert "No chunks are stored" in render_statistics_markdown(statistics)
    finally:
        engine.dispose()
