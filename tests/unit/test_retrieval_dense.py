"""Tests for dense cosine-similarity retrieval."""

import pytest

from neuralnotes.chunking import Chunk
from neuralnotes.retrieval import DenseIndex


def _chunk(chunk_id: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id="paper",
        text=f"text for {chunk_id}",
        page_number=1,
        chunk_index=0,
        start_char=0,
        end_char=len(f"text for {chunk_id}"),
        token_count=3,
        strategy="fixed_size",
    )


def test_dense_index_ranks_by_cosine_and_preserves_ties() -> None:
    index = DenseIndex(((_chunk("aligned"), (1.0, 0.0)), (_chunk("tie"), (1.0, 1.0))))

    hits = index.search((1.0, 0.0), top_k=2)

    assert [hit.chunk.chunk_id for hit in hits] == ["aligned", "tie"]
    assert hits[0].score == pytest.approx(1.0)
    assert hits[1].score == pytest.approx(2**-0.5)


def test_dense_index_returns_empty_for_no_chunks() -> None:
    assert DenseIndex(()).search((1.0, 0.0)) == ()


def test_dense_index_rejects_dimension_mismatch_and_zero_vectors() -> None:
    with pytest.raises(ValueError, match="equal dimensions"):
        DenseIndex(((_chunk("one"), (1.0, 0.0)), (_chunk("two"), (1.0,))))
    with pytest.raises(ValueError, match="non-zero norm"):
        DenseIndex(((_chunk("zero"), (0.0, 0.0)),))


def test_dense_index_rejects_invalid_query_vectors_and_top_k() -> None:
    index = DenseIndex(((_chunk("one"), (1.0, 0.0)),))
    with pytest.raises(ValueError, match="dimension"):
        index.search((1.0,))
    with pytest.raises(ValueError, match="non-zero norm"):
        index.search((0.0, 0.0))
    with pytest.raises(ValueError, match="top_k"):
        index.search((1.0, 0.0), top_k=0)
