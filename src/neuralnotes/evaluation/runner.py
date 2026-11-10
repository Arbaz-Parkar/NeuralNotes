"""Map evidence spans to chunks and aggregate retrieval ranking metrics."""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass

from neuralnotes.chunking import Chunk
from neuralnotes.evaluation.dataset import EvaluationCase
from neuralnotes.retrieval.metrics import (
    hit_rate_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
)

Retriever = Callable[[str, int], Iterable[str]]
_METRICS = {
    "precision": precision_at_k,
    "recall": recall_at_k,
    "hit_rate": hit_rate_at_k,
    "mrr": reciprocal_rank_at_k,
    "ndcg": ndcg_at_k,
}


@dataclass(frozen=True, slots=True)
class QueryEvaluation:
    """Per-question retrieval metrics and the number of relevant chunks."""

    query_id: str
    relevant_chunk_count: int
    metrics_at_k: dict[str, dict[str, float]]


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Aggregate retrieval metrics for one split and retrieval configuration."""

    split: str
    answerable_query_count: int
    excluded_unanswerable_query_count: int
    k_values: tuple[int, ...]
    metrics_at_k: dict[str, dict[str, float]]
    per_query: tuple[QueryEvaluation, ...]
    unanswerable_query_count: int = 0
    unanswerable_empty_result_count: int = 0
    unanswerable_empty_result_rate: float | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of this report."""
        return asdict(self)


def relevant_chunk_ids(
    chunks: Iterable[Chunk],
    case: EvaluationCase,
    *,
    minimum_evidence_overlap: float = 0.5,
) -> frozenset[str]:
    """Find chunks covering the configured fraction of any labeled evidence span."""
    if not 0.0 < minimum_evidence_overlap <= 1.0:
        raise ValueError(
            "minimum_evidence_overlap must be greater than 0 and at most 1."
        )
    if not case.answerable:
        return frozenset()

    relevant: set[str] = set()
    for chunk in chunks:
        for evidence in case.evidence:
            if (
                chunk.document_id != evidence.document_id
                or chunk.page_number != evidence.page_number
            ):
                continue
            overlap = max(
                0,
                min(chunk.end_char, evidence.end_char)
                - max(chunk.start_char, evidence.start_char),
            )
            evidence_length = evidence.end_char - evidence.start_char
            if overlap / evidence_length >= minimum_evidence_overlap:
                relevant.add(chunk.chunk_id)
                break
    return frozenset(relevant)


def evaluate_retrieval(
    cases: Sequence[EvaluationCase],
    chunks: Sequence[Chunk],
    retrieve: Retriever,
    *,
    k_values: tuple[int, ...] = (5, 10, 20),
    minimum_evidence_overlap: float = 0.5,
) -> EvaluationReport:
    """Score verified cases and macro-average metrics over answerable questions."""
    if not cases:
        raise ValueError("At least one evaluation case is required.")
    if not k_values or any(
        isinstance(k, bool) or not isinstance(k, int) or k < 1 for k in k_values
    ):
        raise ValueError("k_values must contain positive integers.")
    if len(set(k_values)) != len(k_values):
        raise ValueError("k_values must not contain duplicates.")

    selected_cases = tuple(case for case in cases if case.verified)
    if not selected_cases:
        raise ValueError("Evaluation requires verified cases.")
    splits = {case.split for case in selected_cases}
    if len(splits) != 1:
        raise ValueError("An evaluation run must use exactly one dataset split.")

    answerable = tuple(case for case in selected_cases if case.answerable)
    unanswerable = tuple(case for case in selected_cases if not case.answerable)
    if not answerable:
        raise ValueError("Evaluation requires at least one verified answerable case.")

    max_k = max(k_values)
    per_query: list[QueryEvaluation] = []
    totals = {str(k): {name: 0.0 for name in _METRICS} for k in k_values}
    for case in answerable:
        relevant = relevant_chunk_ids(
            chunks, case, minimum_evidence_overlap=minimum_evidence_overlap
        )
        if not relevant:
            raise ValueError(
                f"No chunks overlap evidence for verified query {case.query_id}."
            )
        ranked_ids = tuple(retrieve(case.question, max_k))
        metrics_at_k: dict[str, dict[str, float]] = {}
        for k in k_values:
            key = str(k)
            values = {
                name: metric(ranked_ids, relevant, k)
                for name, metric in _METRICS.items()
            }
            metrics_at_k[key] = values
            for name, value in values.items():
                totals[key][name] += value
        per_query.append(
            QueryEvaluation(
                query_id=case.query_id,
                relevant_chunk_count=len(relevant),
                metrics_at_k=metrics_at_k,
            )
        )

    count = len(answerable)
    aggregate = {
        key: {name: value / count for name, value in metrics.items()}
        for key, metrics in totals.items()
    }
    empty_result_count = sum(
        not tuple(retrieve(case.question, max_k)) for case in unanswerable
    )
    return EvaluationReport(
        split=next(iter(splits)),
        answerable_query_count=count,
        excluded_unanswerable_query_count=sum(
            not case.answerable for case in selected_cases
        ),
        k_values=k_values,
        metrics_at_k=aggregate,
        per_query=tuple(per_query),
        unanswerable_query_count=len(unanswerable),
        unanswerable_empty_result_count=empty_result_count,
        unanswerable_empty_result_rate=(
            empty_result_count / len(unanswerable) if unanswerable else None
        ),
    )
