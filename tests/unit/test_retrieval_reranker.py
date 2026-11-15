"""Tests for cross-encoder reranking behavior."""

import pytest

from neuralnotes.chunking import Chunk
from neuralnotes.retrieval import CrossEncoderReranker


class FakeCrossEncoder:
    def __init__(
        self, scores: tuple[float, ...], *, expected_batch_size: int = 16
    ) -> None:
        self.scores = scores
        self.expected_batch_size = expected_batch_size
        self.pairs: tuple[tuple[str, str], ...] = ()

    def predict(self, sentences, *, batch_size: int, show_progress_bar: bool):
        self.pairs = tuple(sentences)
        assert batch_size == self.expected_batch_size
        assert show_progress_bar is False
        return self.scores


def _chunk(chunk_id: str) -> Chunk:
    text = f"passage {chunk_id}"
    return Chunk(
        chunk_id=chunk_id,
        document_id="paper",
        text=text,
        page_number=1,
        chunk_index=0,
        start_char=0,
        end_char=len(text),
        token_count=2,
        strategy="fixed_size",
    )


def test_reranker_orders_candidates_by_score_and_keeps_tie_order() -> None:
    model = FakeCrossEncoder((0.2, 0.9, 0.9), expected_batch_size=8)
    reranker = CrossEncoderReranker(model=model, batch_size=8)

    hits = reranker.rerank(
        "find evidence",
        (_chunk("first"), _chunk("second"), _chunk("third")),
        top_k=2,
    )

    assert [hit.chunk.chunk_id for hit in hits] == ["second", "third"]
    assert [hit.score for hit in hits] == [0.9, 0.9]
    assert model.pairs == (
        ("find evidence", "passage first"),
        ("find evidence", "passage second"),
        ("find evidence", "passage third"),
    )


def test_reranker_handles_empty_candidates_without_model_call() -> None:
    model = FakeCrossEncoder(())

    assert CrossEncoderReranker(model=model).rerank("query", (), top_k=5) == ()
    assert model.pairs == ()


def test_reranker_rejects_invalid_query_top_k_and_score_count() -> None:
    chunk = _chunk("candidate")
    with pytest.raises(ValueError, match="query"):
        CrossEncoderReranker(model=FakeCrossEncoder((1.0,))).rerank(
            " ", (chunk,), top_k=1
        )
    with pytest.raises(ValueError, match="top_k"):
        CrossEncoderReranker(model=FakeCrossEncoder((1.0,))).rerank(
            "query", (chunk,), top_k=0
        )
    with pytest.raises(ValueError, match="score count"):
        CrossEncoderReranker(model=FakeCrossEncoder(())).rerank(
            "query", (chunk,), top_k=1
        )


def test_reranker_rejects_non_finite_scores() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        CrossEncoderReranker(model=FakeCrossEncoder((float("nan"),))).rerank(
            "query", (_chunk("candidate"),), top_k=1
        )
