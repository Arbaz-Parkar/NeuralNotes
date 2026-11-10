"""Tests for reciprocal rank fusion."""

import pytest

from neuralnotes.retrieval import reciprocal_rank_fusion


def test_fusion_combines_rankings_and_sorts_by_fused_score() -> None:
    hits = reciprocal_rank_fusion((("a", "b", "c"), ("c", "b", "d")), rank_constant=1)

    assert [hit.chunk_id for hit in hits] == ["c", "b", "a", "d"]
    assert hits[0].score == pytest.approx(1 / 4 + 1 / 2)
    assert hits[1].score == pytest.approx(1 / 3 + 1 / 3)


def test_duplicate_ids_in_one_ranking_only_use_the_first_rank() -> None:
    hits = reciprocal_rank_fusion((("a", "a", "b"),), rank_constant=0)

    assert [hit.chunk_id for hit in hits] == ["a", "b"]
    assert [hit.score for hit in hits] == [1.0, 1 / 3]


def test_fusion_ties_keep_first_seen_order_and_honors_top_k() -> None:
    hits = reciprocal_rank_fusion((("first",), ("second",)), rank_constant=4, top_k=1)

    assert [hit.chunk_id for hit in hits] == ["first"]


@pytest.mark.parametrize("rank_constant", (-1, float("inf"), float("nan")))
def test_fusion_rejects_invalid_rank_constant(rank_constant: float) -> None:
    with pytest.raises(ValueError, match="rank_constant"):
        reciprocal_rank_fusion((), rank_constant=rank_constant)


def test_fusion_rejects_invalid_ids_and_top_k() -> None:
    with pytest.raises(ValueError, match="non-empty strings"):
        reciprocal_rank_fusion((("valid", ""),))
    with pytest.raises(ValueError, match="top_k"):
        reciprocal_rank_fusion((), top_k=0)
