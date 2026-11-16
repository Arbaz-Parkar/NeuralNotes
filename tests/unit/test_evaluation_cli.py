"""Tests for invoking the BM25 evaluation command."""

import json
from pathlib import Path
from uuid import uuid4

import pytest

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


@pytest.mark.parametrize(
    ("retrieval_method", "retriever_name"),
    (
        ("hybrid", "BM25 + dense RRF"),
        ("dense", "Dense"),
        ("bm25_prf", "BM25 + pseudo-relevance query expansion"),
        ("langchain_bm25", "LangChain BM25Retriever"),
    ),
)
def test_cli_can_evaluate_dense_or_hybrid_retrieval_with_cross_encoder(
    tmp_path: Path,
    monkeypatch,
    retrieval_method: str,
    retriever_name: str,
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

    class FakeEmbedder:
        def __init__(self, *, model_name: str) -> None:
            assert model_name == "test-embedder"

        def embed_query(self, _query: str) -> tuple[float, float]:
            return (1.0, 0.0)

    class FakeReranker:
        def __init__(self, *, model_name: str) -> None:
            assert model_name == "test-reranker"

        def warm_up(self) -> None:
            return None

        def rerank(self, _query, candidates, *, top_k):
            return tuple(
                type("Hit", (), {"chunk": candidate})()
                for candidate in candidates[:top_k]
            )

    class FakeLangChainRetriever:
        def __init__(self, chunks, *, k1: float, b: float, top_k: int) -> None:
            assert tuple(chunks) == (chunk,)
            assert k1 == 1.5
            assert b == 0.75
            assert top_k == 1

        def search(self, _query: str) -> tuple[str, ...]:
            return ("relevant",)

    monkeypatch.setattr(cli, "load_cases", lambda *_args, **_kwargs: (case,))
    monkeypatch.setattr(cli, "create_database_engine", lambda: FakeEngine())
    monkeypatch.setattr(
        cli, "create_database_session_factory", lambda _engine: FakeSessionContext
    )
    monkeypatch.setattr(cli, "load_workspace_chunks", lambda *_args: (chunk,))
    monkeypatch.setattr(
        cli,
        "load_workspace_chunk_embeddings",
        lambda *_args: ((chunk, (1.0, 0.0)),),
    )
    monkeypatch.setattr(
        cli, "get_workspace_embedding_model", lambda *_args: "test-embedder"
    )
    monkeypatch.setattr(cli, "SentenceTransformerEmbedder", FakeEmbedder)
    monkeypatch.setattr(cli, "CrossEncoderReranker", FakeReranker)
    monkeypatch.setattr(cli, "LangChainBM25Retriever", FakeLangChainRetriever)

    result = cli.main(
        [
            "--dataset",
            str(tmp_path / "cases.jsonl"),
            "--dataset-version",
            "dev-v2",
            "--split",
            "dev",
            "--workspace-id",
            str(workspace_id),
            "--output-dir",
            str(tmp_path / "reports"),
            "--k-values",
            "1",
            "--retrieval-method",
            retrieval_method,
            "--reranker-model",
            "test-reranker",
            "--reranker-candidate-count",
            "1",
        ]
    )

    report_path = next((tmp_path / "reports").glob("*.json"))
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert result == 0
    assert payload["retriever"]["name"] == retriever_name
    assert payload["reranker"] == {
        "model": "test-reranker",
        "candidate_count": 1,
    }
