"""Tests for BM25 answerability-threshold calibration and reporting."""

import json
from uuid import uuid4

import pytest

from neuralnotes.evaluation.answerability import (
    AnswerabilityObservation,
    calibrate_answerability_threshold,
    evaluate_answerability_threshold,
    main,
    write_answerability_report,
)


def _observations() -> tuple[AnswerabilityObservation, ...]:
    return (
        AnswerabilityObservation("a1", True, 4.0),
        AnswerabilityObservation("a2", True, 1.0),
        AnswerabilityObservation("u1", False, 0.4),
        AnswerabilityObservation("u2", False, None),
    )


def test_fixed_threshold_reports_confusion_metrics() -> None:
    metrics, predictions = evaluate_answerability_threshold(_observations(), 1.0)

    assert metrics.true_positive == 2
    assert metrics.false_positive == 0
    assert metrics.true_negative == 2
    assert metrics.false_negative == 0
    assert metrics.balanced_accuracy == 1.0
    assert [item.predicted_answerable for item in predictions] == [
        True,
        True,
        False,
        False,
    ]


def test_calibration_selects_threshold_by_balanced_accuracy() -> None:
    metrics, _ = calibrate_answerability_threshold(_observations())

    assert metrics.threshold == 1.0
    assert metrics.balanced_accuracy == 1.0


def test_calibration_requires_both_answerability_labels() -> None:
    with pytest.raises(ValueError, match="answerable and unanswerable"):
        calibrate_answerability_threshold((AnswerabilityObservation("a1", True, 1.0),))


@pytest.mark.parametrize(
    ("observations", "threshold", "message"),
    [
        ((), 1.0, "At least one"),
        (
            (
                AnswerabilityObservation("q1", True, 1.0),
                AnswerabilityObservation("q1", False, 0.0),
            ),
            1.0,
            "unique query ids",
        ),
        ((AnswerabilityObservation("q1", True, -1.0),), 1.0, "nonnegative"),
        ((AnswerabilityObservation("q1", True, 1.0),), -1.0, "threshold"),
    ],
)
def test_calibration_rejects_invalid_inputs(observations, threshold, message) -> None:
    with pytest.raises(ValueError, match=message):
        evaluate_answerability_threshold(observations, threshold)


def test_report_writer_records_metrics_and_query_scores(tmp_path) -> None:
    observations = _observations()
    metrics, predictions = evaluate_answerability_threshold(observations, 1.0)
    workspace_id = uuid4()

    json_path, markdown_path = write_answerability_report(
        metrics,
        predictions,
        tmp_path,
        dataset_version="pilot-v1",
        workspace_id=workspace_id,
        split="dev",
        run_id="run-001",
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert payload["workspace_id"] == str(workspace_id)
    assert payload["metrics"]["threshold"] == 1.0
    assert payload["per_query"][2]["top_score"] == 0.4
    assert "Balanced accuracy: 1.0000" in markdown


def test_test_cli_requires_a_fixed_threshold(tmp_path) -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "--dataset",
                str(tmp_path / "golden.jsonl"),
                "--dataset-version",
                "pilot-v1",
                "--split",
                "test",
                "--workspace-id",
                str(uuid4()),
            ]
        )
