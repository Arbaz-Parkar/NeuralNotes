"""Ranking metrics for retrieval evaluation."""

from collections.abc import Iterable
from math import log2


def precision_at_k(
    retrieved_ids: Iterable[str], relevant_ids: Iterable[str], k: int
) -> float:
    """Return the fraction of the top ``k`` results that are relevant."""
    _validate_k(k)
    relevant = set(relevant_ids)
    retrieved = tuple(retrieved_ids)[:k]
    return len(_unique_relevant_hits(retrieved, relevant)) / k


def recall_at_k(
    retrieved_ids: Iterable[str], relevant_ids: Iterable[str], k: int
) -> float:
    """Return the fraction of known relevant items found in the top ``k``."""
    _validate_k(k)
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    retrieved = tuple(retrieved_ids)[:k]
    return len(_unique_relevant_hits(retrieved, relevant)) / len(relevant)


def hit_rate_at_k(
    retrieved_ids: Iterable[str], relevant_ids: Iterable[str], k: int
) -> float:
    """Return 1 when the top ``k`` contains relevant evidence, otherwise 0."""
    _validate_k(k)
    relevant = set(relevant_ids)
    return float(bool(_unique_relevant_hits(tuple(retrieved_ids)[:k], relevant)))


def reciprocal_rank_at_k(
    retrieved_ids: Iterable[str], relevant_ids: Iterable[str], k: int
) -> float:
    """Return the reciprocal rank of the first relevant result within ``k``."""
    _validate_k(k)
    relevant = set(relevant_ids)
    seen: set[str] = set()
    for rank, item_id in enumerate(retrieved_ids, start=1):
        if rank > k:
            break
        if item_id in relevant and item_id not in seen:
            return 1.0 / rank
        seen.add(item_id)
    return 0.0


def ndcg_at_k(
    retrieved_ids: Iterable[str], relevant_ids: Iterable[str], k: int
) -> float:
    """Return binary-gain normalized discounted cumulative gain at ``k``."""
    _validate_k(k)
    relevant = set(relevant_ids)
    retrieved = tuple(retrieved_ids)[:k]
    unique_relevant = set(_unique_relevant_hits(retrieved, relevant))
    dcg = sum(
        1.0 / log2(rank + 1)
        for rank, item_id in enumerate(retrieved, start=1)
        if item_id in unique_relevant and item_id not in retrieved[: rank - 1]
    )
    ideal_relevant_count = min(len(relevant), k)
    if ideal_relevant_count == 0:
        return 0.0
    ideal_dcg = sum(1.0 / log2(rank + 1) for rank in range(1, ideal_relevant_count + 1))
    return dcg / ideal_dcg


def _validate_k(k: int) -> None:
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k must be a positive integer.")


def _unique_relevant_hits(
    retrieved: Iterable[str], relevant: set[str]
) -> tuple[str, ...]:
    seen: set[str] = set()
    hits: list[str] = []
    for item_id in retrieved:
        if item_id in relevant and item_id not in seen:
            hits.append(item_id)
        seen.add(item_id)
    return tuple(hits)
