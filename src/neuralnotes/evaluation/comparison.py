"""Paired bootstrap comparison of two retrieval evaluation reports."""

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from math import isfinite
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from neuralnotes.evaluation.statistics import (
    BootstrapInterval,
    paired_bootstrap_difference,
)


class _QueryMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(min_length=1)
    metrics_at_k: dict[str, dict[str, float]]


class _EvaluationInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    report_schema_version: Literal[2]
    dataset_version: str = Field(
        min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
    )
    workspace_id: UUID
    split: Literal["dev", "test"]
    k_values: tuple[int, ...]
    per_query: tuple[_QueryMetrics, ...]

    @model_validator(mode="after")
    def validate_queries(self) -> "_EvaluationInput":
        if not self.k_values or any(k < 1 for k in self.k_values):
            raise ValueError("Evaluation reports must use positive ranking cutoffs.")
        if len(self.k_values) != len(set(self.k_values)):
            raise ValueError("Evaluation reports must not repeat ranking cutoffs.")
        query_ids = tuple(query.query_id for query in self.per_query)
        if not query_ids:
            raise ValueError("Evaluation reports must contain per-query results.")
        if len(query_ids) != len(set(query_ids)):
            raise ValueError("Evaluation reports must not contain duplicate query ids.")
        expected_keys = {str(k) for k in self.k_values}
        expected_metrics: set[str] | None = None
        for query in self.per_query:
            if set(query.metrics_at_k) != expected_keys:
                raise ValueError("Per-query metrics must contain every report cutoff.")
            for values in query.metrics_at_k.values():
                metric_names = set(values)
                if not metric_names:
                    raise ValueError("Per-query metric sets must not be empty.")
                if expected_metrics is None:
                    expected_metrics = metric_names
                elif metric_names != expected_metrics:
                    raise ValueError(
                        "Per-query metric names must match across reports."
                    )
                if not all(isfinite(value) for value in values.values()):
                    raise ValueError("Per-query metric values must be finite.")
        return self


@dataclass(frozen=True, slots=True)
class ComparisonReport:
    """Paired candidate-minus-baseline intervals for matching evaluation queries."""

    dataset_version: str
    split: str
    baseline_workspace_id: UUID
    candidate_workspace_id: UUID
    query_count: int
    k_values: tuple[int, ...]
    metric_differences_at_k: dict[str, dict[str, BootstrapInterval]]
    confidence_level: float
    resamples: int
    seed: int


def compare_evaluation_reports(
    baseline_payload: Mapping[str, object],
    candidate_payload: Mapping[str, object],
    *,
    confidence_level: float = 0.95,
    resamples: int = 2_000,
    seed: int = 0,
) -> ComparisonReport:
    """Compare matching per-query scores using paired bootstrap differences."""
    baseline = _EvaluationInput.model_validate(baseline_payload)
    candidate = _EvaluationInput.model_validate(candidate_payload)
    if baseline.dataset_version != candidate.dataset_version:
        raise ValueError("Reports must use the same dataset version.")
    if baseline.split != candidate.split:
        raise ValueError("Reports must use the same dataset split.")
    if baseline.k_values != candidate.k_values:
        raise ValueError("Reports must use the same ranking cutoffs.")

    baseline_by_id = {query.query_id: query for query in baseline.per_query}
    candidate_by_id = {query.query_id: query for query in candidate.per_query}
    if baseline_by_id.keys() != candidate_by_id.keys():
        raise ValueError("Reports must contain the same query ids.")

    difference_intervals: dict[str, dict[str, BootstrapInterval]] = {}
    for k in baseline.k_values:
        key = str(k)
        baseline_metrics = baseline.per_query[0].metrics_at_k[key]
        candidate_metrics = candidate.per_query[0].metrics_at_k[key]
        if baseline_metrics.keys() != candidate_metrics.keys():
            raise ValueError("Reports must contain the same metric names.")
        difference_intervals[key] = {}
        for metric_name in baseline_metrics:
            for query_id in baseline_by_id:
                if (
                    baseline_by_id[query_id].metrics_at_k[key].keys()
                    != candidate_by_id[query_id].metrics_at_k[key].keys()
                ):
                    raise ValueError(
                        "Reports must contain the same metric names per query."
                    )
            difference_intervals[key][metric_name] = paired_bootstrap_difference(
                (
                    baseline_by_id[query_id].metrics_at_k[key][metric_name]
                    for query_id in baseline_by_id
                ),
                (
                    candidate_by_id[query_id].metrics_at_k[key][metric_name]
                    for query_id in baseline_by_id
                ),
                confidence_level=confidence_level,
                resamples=resamples,
                seed=seed,
            )

    return ComparisonReport(
        dataset_version=baseline.dataset_version,
        split=baseline.split,
        baseline_workspace_id=baseline.workspace_id,
        candidate_workspace_id=candidate.workspace_id,
        query_count=len(baseline_by_id),
        k_values=baseline.k_values,
        metric_differences_at_k=difference_intervals,
        confidence_level=confidence_level,
        resamples=resamples,
        seed=seed,
    )


def write_comparison_report(
    report: ComparisonReport,
    output_dir: Path,
    *,
    run_id: str,
) -> tuple[Path, Path]:
    """Write a JSON record and Markdown summary for a paired comparison."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", run_id):
        raise ValueError(
            "run_id must start with a letter or digit and contain only letters, "
            "digits, dots, underscores, or hyphens."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{report.dataset_version}__paired__{report.split}__{run_id}"
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"
    payload = {
        "comparison_schema_version": 1,
        "dataset_version": report.dataset_version,
        "split": report.split,
        "baseline_workspace_id": str(report.baseline_workspace_id),
        "candidate_workspace_id": str(report.candidate_workspace_id),
        "query_count": report.query_count,
        "k_values": report.k_values,
        "candidate_minus_baseline": {
            key: {metric: asdict(interval) for metric, interval in metrics.items()}
            for key, metrics in report.metric_differences_at_k.items()
        },
        "bootstrap": {
            "method": "paired_percentile",
            "confidence_level": report.confidence_level,
            "resamples": report.resamples,
            "seed": report.seed,
        },
    }
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(_render_comparison_markdown(payload), encoding="utf-8")
    return json_path, markdown_path


def _render_comparison_markdown(payload: dict[str, object]) -> str:
    differences = payload["candidate_minus_baseline"]
    bootstrap = payload["bootstrap"]
    assert isinstance(differences, dict)
    assert isinstance(bootstrap, dict)
    lines = [
        f"# Paired retrieval comparison — {payload['dataset_version']}",
        "",
        "> Positive differences favor the candidate report; negative differences "
        "favor the baseline. The interval is not a substitute for checking dataset "
        "quality and sample size.",
        "",
        f"- Split: `{payload['split']}`",
        f"- Paired queries: {payload['query_count']}",
        f"- Baseline workspace: `{payload['baseline_workspace_id']}`",
        f"- Candidate workspace: `{payload['candidate_workspace_id']}`",
        f"- Bootstrap: paired percentile, {bootstrap['resamples']} resamples, "
        f"seed {bootstrap['seed']}, confidence {bootstrap['confidence_level']:.1%}",
        "",
        "| k | Metric | Candidate − baseline | Confidence interval |",
        "| ---: | --- | ---: | ---: |",
    ]
    for key, metrics in differences.items():
        for metric_name, interval in metrics.items():
            lines.append(
                f"| {key} | {metric_name} | {interval['mean']:+.4f} | "
                f"[{interval['lower']:+.4f}, {interval['upper']:+.4f}] |"
            )
    lines.extend(
        (
            "",
            "Do not choose a retrieval configuration using a held-out test split. "
            "Small query sets produce unstable intervals.",
            "",
        )
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Compare two JSON run reports and write a paired comparison."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/evaluations/comparisons"),
    )
    parser.add_argument("--confidence-level", type=float, default=0.95)
    parser.add_argument("--resamples", type=int, default=2_000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    report = compare_evaluation_reports(
        baseline,
        candidate,
        confidence_level=args.confidence_level,
        resamples=args.resamples,
        seed=args.seed,
    )
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    json_path, markdown_path = write_comparison_report(
        report, args.output_dir, run_id=run_id
    )
    print(f"Wrote comparison JSON to {json_path}")
    print(f"Wrote comparison Markdown to {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
