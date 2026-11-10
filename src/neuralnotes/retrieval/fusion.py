"""Reciprocal rank fusion for combining independent retrieval rankings."""

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class FusionHit:
    """A unique result and its reciprocal-rank fusion score."""

    chunk_id: str
    score: float


def reciprocal_rank_fusion(
    rankings: Iterable[Iterable[str]],
    *,
    rank_constant: float = 60.0,
    top_k: int | None = None,
) -> tuple[FusionHit, ...]:
    """Combine ranked chunk ids with ``sum(1 / (rank_constant + rank))``.

    Ranks are one-based. Repeated ids in an individual ranking contribute only
    their first rank. Ties preserve the order in which ids first appeared while
    traversing the input rankings.
    """
    if not isfinite(rank_constant) or rank_constant < 0:
        raise ValueError("rank_constant must be a finite non-negative number.")
    if top_k is not None and top_k < 1:
        raise ValueError("top_k must be at least one when provided.")

    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    next_order = 0

    for ranking in rankings:
        seen_in_ranking: set[str] = set()
        for rank, chunk_id in enumerate(ranking, start=1):
            if not isinstance(chunk_id, str) or not chunk_id:
                raise ValueError("ranked chunk ids must be non-empty strings.")
            if chunk_id in seen_in_ranking:
                continue
            seen_in_ranking.add(chunk_id)

            if chunk_id not in scores:
                scores[chunk_id] = 0.0
                first_seen[chunk_id] = next_order
                next_order += 1
            scores[chunk_id] += 1.0 / (rank_constant + rank)

    ordered = sorted(
        scores, key=lambda chunk_id: (-scores[chunk_id], first_seen[chunk_id])
    )
    if top_k is not None:
        ordered = ordered[:top_k]
    return tuple(FusionHit(chunk_id, scores[chunk_id]) for chunk_id in ordered)
