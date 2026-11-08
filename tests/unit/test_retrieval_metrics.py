"""Known-answer tests for retrieval ranking metrics."""

import pytest

from neuralnotes.retrieval.metrics import (
    hit_rate_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
)


@pytest.mark.parametrize(
    ("metric", "expected"),
    [
        (precision_at_k, 2 / 3),
        (recall_at_k, 1.0),
        (hit_rate_at_k, 1.0),
        (reciprocal_rank_at_k, 0.5),
    ],
)
def test_metrics_match_known_ranking(metric, expected: float) -> None:
    retrieved = ["noise", "relevant-a", "relevant-b"]
    relevant = {"relevant-a", "relevant-b"}
    assert metric(retrieved, relevant, 3) == pytest.approx(expected)


def test_ndcg_rewards_relevant_results_near_the_top() -> None:
    relevant = {"a", "b"}

    assert ndcg_at_k(["a", "b", "noise"], relevant, 3) == pytest.approx(1.0)
    assert ndcg_at_k(["noise", "a", "b"], relevant, 3) < 1.0


def test_empty_relevance_has_zero_scores() -> None:
    retrieved = ["a", "b"]

    assert precision_at_k(retrieved, set(), 2) == 0.0
    assert recall_at_k(retrieved, set(), 2) == 0.0
    assert hit_rate_at_k(retrieved, set(), 2) == 0.0
    assert reciprocal_rank_at_k(retrieved, set(), 2) == 0.0
    assert ndcg_at_k(retrieved, set(), 2) == 0.0


@pytest.mark.parametrize("k", [0, -1, 1.5, True])
def test_metrics_reject_invalid_k(k: int) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        precision_at_k([], [], k)


def test_metrics_accept_generators() -> None:
    assert recall_at_k((item for item in ["a", "b"]), {"b"}, 2) == 1.0


def test_duplicate_results_do_not_inflate_relevance_metrics() -> None:
    retrieved = ["a", "a"]
    relevant = {"a"}

    assert precision_at_k(retrieved, relevant, 2) == 0.5
    assert recall_at_k(retrieved, relevant, 2) == 1.0
    assert ndcg_at_k(retrieved, relevant, 2) == 1.0
