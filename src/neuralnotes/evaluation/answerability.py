"""Calibrate a BM25 score threshold for answerability decisions."""

import argparse
import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from math import inf, isfinite, nextafter
from pathlib import Path
from uuid import UUID

from neuralnotes.database import (
    create_database_engine,
    create_database_session_factory,
)
from neuralnotes.db.retrieval import load_workspace_chunks
from neuralnotes.evaluation.dataset import load_cases
from neuralnotes.retrieval import BM25Index

_SAFE_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


@dataclass(frozen=True, slots=True)
class AnswerabilityObservation:
    """The BM25 top score and gold answerability label for one query."""

    query_id: str
    answerable: bool
    top_score: float | None


@dataclass(frozen=True, slots=True)
class AnswerabilityPrediction:
    """One threshold-based answerability prediction."""

    query_id: str
    answerable: bool
    top_score: float | None
    predicted_answerable: bool


@dataclass(frozen=True, slots=True)
class AnswerabilityMetrics:
    """Confusion counts and rates for a fixed BM25 score threshold."""

    threshold: float
    query_count: int
    answerable_count: int
    unanswerable_count: int
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    accuracy: float
    precision: float
    recall: float
    specificity: float
    f1: float
    balanced_accuracy: float


def evaluate_answerability_threshold(
    observations: Sequence[AnswerabilityObservation], threshold: float
) -> tuple[AnswerabilityMetrics, tuple[AnswerabilityPrediction, ...]]:
    """Score a finite nonnegative threshold against labeled query observations."""
    sample = _validate_observations(observations)
    if not isfinite(threshold) or threshold < 0:
        raise ValueError("threshold must be a finite nonnegative number.")

    predictions = tuple(
        AnswerabilityPrediction(
            query_id=item.query_id,
            answerable=item.answerable,
            top_score=item.top_score,
            predicted_answerable=(
                item.top_score is not None and item.top_score >= threshold
            ),
        )
        for item in sample
    )
    true_positive = sum(
        item.answerable and item.predicted_answerable for item in predictions
    )
    false_positive = sum(
        not item.answerable and item.predicted_answerable for item in predictions
    )
    true_negative = sum(
        not item.answerable and not item.predicted_answerable for item in predictions
    )
    false_negative = sum(
        item.answerable and not item.predicted_answerable for item in predictions
    )

    answerable_count = true_positive + false_negative
    unanswerable_count = true_negative + false_positive
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 0.0
    )
    recall = true_positive / answerable_count if answerable_count else 0.0
    specificity = true_negative / unanswerable_count if unanswerable_count else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    accuracy = (true_positive + true_negative) / len(predictions)
    metrics = AnswerabilityMetrics(
        threshold=threshold,
        query_count=len(predictions),
        answerable_count=answerable_count,
        unanswerable_count=unanswerable_count,
        true_positive=true_positive,
        false_positive=false_positive,
        true_negative=true_negative,
        false_negative=false_negative,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        specificity=specificity,
        f1=f1,
        balanced_accuracy=(recall + specificity) / 2.0,
    )
    return metrics, predictions


def calibrate_answerability_threshold(
    observations: Sequence[AnswerabilityObservation],
) -> tuple[AnswerabilityMetrics, tuple[AnswerabilityPrediction, ...]]:
    """Choose the threshold with best balanced accuracy on calibration data.

    Ties prefer higher specificity, then the higher threshold. Calibration requires
    both answerable and unanswerable examples and should use the dev split only.
    """
    sample = _validate_observations(observations)
    labels = {item.answerable for item in sample}
    if labels != {False, True}:
        raise ValueError(
            "Threshold calibration requires answerable and unanswerable queries."
        )

    scores = tuple(item.top_score for item in sample if item.top_score is not None)
    candidates = {0.0}
    candidates.update(scores)
    if scores:
        candidates.add(nextafter(max(scores), inf))

    evaluated = tuple(
        evaluate_answerability_threshold(sample, threshold)
        for threshold in sorted(candidates)
    )
    return max(
        evaluated,
        key=lambda result: (
            result[0].balanced_accuracy,
            result[0].specificity,
            result[0].threshold,
        ),
    )


def _validate_observations(
    observations: Sequence[AnswerabilityObservation],
) -> tuple[AnswerabilityObservation, ...]:
    sample = tuple(observations)
    if not sample:
        raise ValueError("At least one answerability observation is required.")
    query_ids = tuple(item.query_id for item in sample)
    if any(not query_id.strip() for query_id in query_ids):
        raise ValueError("Query ids must contain non-whitespace text.")
    if len(query_ids) != len(set(query_ids)):
        raise ValueError("Answerability observations must have unique query ids.")
    for item in sample:
        if not isinstance(item.answerable, bool):
            raise ValueError("Answerability labels must be booleans.")
        if item.top_score is not None and (
            not isfinite(item.top_score) or item.top_score < 0
        ):
            raise ValueError("BM25 top scores must be finite and nonnegative.")
    return sample


def write_answerability_report(
    metrics: AnswerabilityMetrics,
    predictions: Sequence[AnswerabilityPrediction],
    output_dir: Path,
    *,
    dataset_version: str,
    workspace_id: UUID,
    split: str,
    run_id: str,
) -> tuple[Path, Path]:
    """Write JSON and Markdown records for calibration or threshold evaluation."""
    if not _SAFE_VERSION.fullmatch(dataset_version):
        raise ValueError("dataset_version contains unsafe filename characters.")
    if not _SAFE_VERSION.fullmatch(run_id):
        raise ValueError("run_id contains unsafe filename characters.")
    if split not in {"dev", "test"}:
        raise ValueError("split must be 'dev' or 'test'.")
    mode = "calibration" if split == "dev" else "threshold_evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{dataset_version}__answerability__{workspace_id}__{split}__{run_id}"
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"
    payload = {
        "answerability_schema_version": 1,
        "mode": mode,
        "dataset_version": dataset_version,
        "workspace_id": str(workspace_id),
        "split": split,
        "metrics": asdict(metrics),
        "per_query": [asdict(item) for item in predictions],
    }
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown = _render_markdown(payload)
    markdown_path.write_text(markdown, encoding="utf-8")
    return json_path, markdown_path


def _render_markdown(payload: dict[str, object]) -> str:
    metrics = payload["metrics"]
    assert isinstance(metrics, dict)
    return "\n".join(
        (
            f"# BM25 answerability — {payload['dataset_version']}",
            "",
            f"- Mode: `{payload['mode']}`",
            f"- Workspace: `{payload['workspace_id']}`",
            f"- Split: `{payload['split']}`",
            f"- Threshold: {metrics['threshold']:.17g}",
            f"- Queries: {metrics['query_count']} "
            f"({metrics['answerable_count']} answerable, "
            f"{metrics['unanswerable_count']} unanswerable)",
            f"- Confusion counts: TP {metrics['true_positive']}, "
            f"FP {metrics['false_positive']}, TN {metrics['true_negative']}, "
            f"FN {metrics['false_negative']}",
            f"- Accuracy: {metrics['accuracy']:.4f}",
            f"- Precision: {metrics['precision']:.4f}",
            f"- Recall: {metrics['recall']:.4f}",
            f"- Specificity: {metrics['specificity']:.4f}",
            f"- F1: {metrics['f1']:.4f}",
            f"- Balanced accuracy: {metrics['balanced_accuracy']:.4f}",
            "",
            "Dev thresholds are selected by maximizing balanced accuracy; ties favor "
            "higher specificity and then the higher threshold. Test runs require a "
            "fixed threshold copied from the matching workspace's dev report.",
            "",
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Calibrate on dev or evaluate a fixed threshold on the test split."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--split", choices=("dev", "test"), required=True)
    parser.add_argument("--workspace-id", type=UUID, required=True)
    parser.add_argument("--threshold", type=float)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/processed/evaluations")
    )
    parser.add_argument("--k1", type=float, default=1.5)
    parser.add_argument("--b", type=float, default=0.75)
    args = parser.parse_args(argv)

    if args.split == "dev" and args.threshold is not None:
        parser.error("--threshold is selected from dev data and cannot be supplied.")
    if args.split == "test" and args.threshold is None:
        parser.error("--split test requires a threshold from the matching dev run.")

    cases = load_cases(args.dataset, split=args.split)
    engine = create_database_engine()
    try:
        session_factory = create_database_session_factory(engine)
        with session_factory() as session:
            chunks = load_workspace_chunks(session, args.workspace_id)
    finally:
        engine.dispose()

    index = BM25Index(chunks, k1=args.k1, b=args.b)
    observations = tuple(
        AnswerabilityObservation(
            query_id=case.query_id,
            answerable=case.answerable,
            top_score=(
                hits[0].score
                if (hits := index.search(case.question, top_k=1))
                else None
            ),
        )
        for case in cases
    )
    if args.split == "dev":
        metrics, predictions = calibrate_answerability_threshold(observations)
    else:
        assert args.threshold is not None
        metrics, predictions = evaluate_answerability_threshold(
            observations, args.threshold
        )

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    json_path, markdown_path = write_answerability_report(
        metrics,
        predictions,
        args.output_dir,
        dataset_version=args.dataset_version,
        workspace_id=args.workspace_id,
        split=args.split,
        run_id=run_id,
    )
    if args.split == "dev":
        print(f"Calibrated BM25 answerability threshold: {metrics.threshold:.17g}")
    print(f"Wrote answerability JSON to {json_path}")
    print(f"Wrote answerability Markdown to {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
