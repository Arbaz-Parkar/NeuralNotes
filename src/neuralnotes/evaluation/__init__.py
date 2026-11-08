"""Data validation and metrics for retrieval experiments."""

from neuralnotes.evaluation.dataset import EvaluationCase, EvidenceSpan, load_cases
from neuralnotes.evaluation.reports import write_evaluation_reports
from neuralnotes.evaluation.runner import (
    EvaluationReport,
    evaluate_retrieval,
    relevant_chunk_ids,
)
from neuralnotes.evaluation.statistics import (
    BootstrapInterval,
    bootstrap_mean_interval,
    paired_bootstrap_difference,
)

__all__ = [
    "EvidenceSpan",
    "EvaluationCase",
    "EvaluationReport",
    "BootstrapInterval",
    "bootstrap_mean_interval",
    "evaluate_retrieval",
    "load_cases",
    "paired_bootstrap_difference",
    "relevant_chunk_ids",
    "write_evaluation_reports",
]
