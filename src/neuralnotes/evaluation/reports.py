"""Versioned JSON and Markdown output for retrieval evaluation runs."""

import json
import re
from pathlib import Path
from uuid import UUID

from neuralnotes.evaluation.runner import EvaluationReport

_SAFE_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


def write_evaluation_reports(
    report: EvaluationReport,
    output_dir: Path,
    *,
    dataset_version: str,
    workspace_id: UUID,
    run_id: str,
    evidence_overlap: float,
    bm25_k1: float,
    bm25_b: float,
    chunk_count: int,
) -> tuple[Path, Path]:
    """Write a reproducible run record and a compact Markdown summary."""
    _validate_version(dataset_version, "dataset_version")
    _validate_version(run_id, "run_id")
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{dataset_version}__{workspace_id}__{report.split}__{run_id}"
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"
    payload = {
        "report_schema_version": 1,
        "run_id": run_id,
        "dataset_version": dataset_version,
        "workspace_id": str(workspace_id),
        "split": report.split,
        "chunk_count": chunk_count,
        "evidence_overlap_threshold": evidence_overlap,
        "retriever": {"name": "BM25", "k1": bm25_k1, "b": bm25_b},
        "answerable_query_count": report.answerable_query_count,
        "excluded_unanswerable_query_count": report.excluded_unanswerable_query_count,
        "k_values": report.k_values,
        "metrics_at_k": report.metrics_at_k,
        "per_query": [
            {
                "query_id": item.query_id,
                "relevant_chunk_count": item.relevant_chunk_count,
                "metrics_at_k": item.metrics_at_k,
            }
            for item in report.per_query
        ],
    }
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    return json_path, markdown_path


def _render_markdown(payload: dict[str, object]) -> str:
    metrics_at_k = payload["metrics_at_k"]
    assert isinstance(metrics_at_k, dict)
    lines = [
        f"# Retrieval evaluation — {payload['dataset_version']}",
        "",
        "> This report describes retrieval metrics for one run. Interpret scores only "
        "when the selected dataset cases have been manually verified.",
        "",
        f"- Run: `{payload['run_id']}`",
        f"- Workspace: `{payload['workspace_id']}`",
        f"- Split: `{payload['split']}`",
        f"- Chunks indexed: {payload['chunk_count']}",
        f"- Answerable queries scored: {payload['answerable_query_count']}",
        f"- Unanswerable queries excluded from ranking averages: "
        f"{payload['excluded_unanswerable_query_count']}",
        f"- Evidence overlap threshold: {payload['evidence_overlap_threshold']}",
        f"- BM25 parameters: `k1={payload['retriever']['k1']}`, "
        f"`b={payload['retriever']['b']}`",
        "",
        "## Macro-averaged ranking metrics",
        "",
        "| k | Precision | Recall | Hit rate | MRR | nDCG |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, values in metrics_at_k.items():
        lines.append(
            f"| {key} | {values['precision']:.4f} | {values['recall']:.4f} | "
            f"{values['hit_rate']:.4f} | {values['mrr']:.4f} | {values['ndcg']:.4f} |"
        )
    lines.extend(
        (
            "",
            "This is a single run. It does not include confidence intervals and is not "
            "evidence that this configuration is better than another.",
            "",
        )
    )
    return "\n".join(lines)


def _validate_version(value: str, field_name: str) -> None:
    if not _SAFE_VERSION.fullmatch(value):
        raise ValueError(
            f"{field_name} must start with a letter or digit and contain only "
            "letters, digits, dots, underscores, or hyphens."
        )
