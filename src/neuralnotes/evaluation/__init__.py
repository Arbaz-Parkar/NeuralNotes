"""Data validation and metrics for retrieval experiments."""

from neuralnotes.evaluation.dataset import EvaluationCase, EvidenceSpan, load_cases
from neuralnotes.evaluation.reports import write_evaluation_reports
from neuralnotes.evaluation.runner import (
    EvaluationReport,
    evaluate_retrieval,
    relevant_chunk_ids,
)

__all__ = [
    "EvidenceSpan",
    "EvaluationCase",
    "EvaluationReport",
    "evaluate_retrieval",
    "load_cases",
    "relevant_chunk_ids",
    "write_evaluation_reports",
]
