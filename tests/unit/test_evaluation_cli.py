"""Tests for invoking the BM25 evaluation command."""

from pathlib import Path
from uuid import uuid4

from neuralnotes.chunking import Chunk
from neuralnotes.evaluation import EvaluationCase, cli


class FakeEngine:
    disposed = False

    def dispose(self) -> None:
        self.disposed = True


class FakeSessionContext:
    def __enter__(self):
        return object()

    def __exit__(self, *_args):
        return False


def test_cli_builds_workspace_index_and_writes_versioned_outputs(
    tmp_path: Path, monkeypatch
) -> None:
    workspace_id = uuid4()
    chunk = Chunk(
        chunk_id="relevant",
        document_id="paper-1",
        text="retrieval evidence",
        page_number=1,
        chunk_index=0,
        start_char=0,
        end_char=19,
        token_count=2,
        strategy="fixed_size",
    )
    case = EvaluationCase(
        query_id="q1",
        question="retrieval evidence",
        split="dev",
        category="single_passage",
        answerable=True,
        evidence=(
            {
                "document_id": "paper-1",
                "page_number": 1,
                "start_char": 0,
                "end_char": 19,
            },
        ),
        verified=True,
    )
    engine = FakeEngine()
    monkeypatch.setattr(cli, "load_cases", lambda *_args, **_kwargs: (case,))
    monkeypatch.setattr(cli, "create_database_engine", lambda: engine)
    monkeypatch.setattr(
        cli, "create_database_session_factory", lambda _engine: FakeSessionContext
    )
    monkeypatch.setattr(cli, "load_workspace_chunks", lambda *_args: (chunk,))

    result = cli.main(
        [
            "--dataset",
            str(tmp_path / "cases.jsonl"),
            "--dataset-version",
            "dev-v1",
            "--split",
            "dev",
            "--workspace-id",
            str(workspace_id),
            "--output-dir",
            str(tmp_path / "reports"),
            "--k-values",
            "1",
        ]
    )

    assert result == 0
    assert engine.disposed
    assert len(list((tmp_path / "reports").glob("*.json"))) == 1
    assert len(list((tmp_path / "reports").glob("*.md"))) == 1
