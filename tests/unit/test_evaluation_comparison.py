"""Tests for paired retrieval report comparison and its command line."""

import json
from pathlib import Path
from uuid import uuid4

import pytest

from neuralnotes.evaluation.comparison import (
    compare_evaluation_reports,
    main,
    write_comparison_report,
)


def _run(
    workspace_id: str,
    scores: tuple[float, ...],
    *,
    version: str = "pilot-v1",
    split: str = "dev",
    cutoffs: tuple[int, ...] = (1,),
    query_ids: tuple[str, ...] = ("q1", "q2", "q3"),
) -> dict[str, object]:
    return {
        "report_schema_version": 2,
        "dataset_version": version,
        "workspace_id": workspace_id,
        "split": split,
        "k_values": list(cutoffs),
        "per_query": [
            {
                "query_id": query_id,
                "metrics_at_k": {
                    str(k): {"recall": score, "ndcg": score} for k in cutoffs
                },
            }
            for query_id, score in zip(query_ids, scores, strict=True)
        ],
    }


def test_comparison_pairs_query_scores_and_uses_candidate_minus_baseline() -> None:
    baseline = _run(str(uuid4()), (0.1, 0.6, 0.8))
    candidate = _run(str(uuid4()), (0.9, 0.2, 0.6), query_ids=("q3", "q1", "q2"))

    report = compare_evaluation_reports(baseline, candidate, resamples=500, seed=11)

    assert report.query_count == 3
    assert report.metric_differences_at_k["1"]["recall"].mean == pytest.approx(
        (0.1 + 0.1 + 0.0) / 3
    )
    assert report.baseline_workspace_id != report.candidate_workspace_id


@pytest.mark.parametrize(
    ("candidate_changes", "message"),
    [
        ({"dataset_version": "pilot-v2"}, "same dataset version"),
        ({"split": "test"}, "same dataset split"),
        ({"query_ids": ("q1", "q2", "q4")}, "same query ids"),
        ({"cutoffs": (5,)}, "same ranking cutoffs"),
    ],
)
def test_comparison_rejects_unpaired_or_mismatched_reports(
    candidate_changes: dict[str, object], message: str
) -> None:
    baseline = _run(str(uuid4()), (0.1, 0.6, 0.8))
    candidate_args: dict[str, object] = {"workspace_id": str(uuid4())}
    if "dataset_version" in candidate_changes:
        candidate_args["version"] = candidate_changes["dataset_version"]
    if "split" in candidate_changes:
        candidate_args["split"] = candidate_changes["split"]
    if "query_ids" in candidate_changes:
        candidate_args["query_ids"] = candidate_changes["query_ids"]
    if "cutoffs" in candidate_changes:
        candidate_args["cutoffs"] = candidate_changes["cutoffs"]
    candidate = _run(
        str(candidate_args.pop("workspace_id")),
        (0.2, 0.6, 0.9),
        **candidate_args,
    )

    with pytest.raises(ValueError, match=message):
        compare_evaluation_reports(baseline, candidate)


def test_comparison_writer_saves_json_and_markdown(tmp_path: Path) -> None:
    report = compare_evaluation_reports(
        _run(str(uuid4()), (0.1, 0.6, 0.8)),
        _run(str(uuid4()), (0.2, 0.6, 0.9)),
        resamples=100,
    )

    json_path, markdown_path = write_comparison_report(
        report, tmp_path, run_id="compare-1"
    )

    result = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert result["query_count"] == 3
    assert "candidate_minus_baseline" in result
    assert "Positive differences favor the candidate" in markdown


def test_comparison_cli_reads_runs_and_writes_outputs(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    baseline_path.write_text(
        json.dumps(_run(str(uuid4()), (0.1, 0.6, 0.8))), encoding="utf-8"
    )
    candidate_path.write_text(
        json.dumps(_run(str(uuid4()), (0.2, 0.6, 0.9))), encoding="utf-8"
    )
    output_dir = tmp_path / "results"

    result = main(
        [
            "--baseline",
            str(baseline_path),
            "--candidate",
            str(candidate_path),
            "--output-dir",
            str(output_dir),
            "--resamples",
            "100",
        ]
    )

    assert result == 0
    assert len(list(output_dir.glob("*.json"))) == 1
    assert len(list(output_dir.glob("*.md"))) == 1
