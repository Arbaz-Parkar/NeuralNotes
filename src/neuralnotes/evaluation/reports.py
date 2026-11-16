"""Versioned JSON and Markdown output for retrieval evaluation runs."""

import json
import re
from dataclasses import asdict
from pathlib import Path
from uuid import UUID

from neuralnotes.evaluation.runner import EvaluationReport
from neuralnotes.evaluation.statistics import bootstrap_mean_interval

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
    retrieval_method: str = "bm25",
    rrf_constant: float | None = None,
    feedback_document_count: int = 5,
    feedback_term_count: int = 5,
    embedding_model: str | None = None,
    reranker_model: str | None = None,
    reranker_candidate_count: int | None = None,
    confidence_level: float = 0.95,
    bootstrap_resamples: int = 2_000,
    bootstrap_seed: int = 0,
) -> tuple[Path, Path]:
    """Write a reproducible run record and a compact Markdown summary."""
    _validate_version(dataset_version, "dataset_version")
    _validate_version(run_id, "run_id")
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{dataset_version}__{workspace_id}__{report.split}__{run_id}"
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"
    confidence_intervals: dict[str, dict[str, dict[str, float | int]]] = {}
    for k in report.k_values:
        key = str(k)
        confidence_intervals[key] = {}
        for metric_name in report.metrics_at_k[key]:
            values = tuple(
                item.metrics_at_k[key][metric_name] for item in report.per_query
            )
            interval = bootstrap_mean_interval(
                values,
                confidence_level=confidence_level,
                resamples=bootstrap_resamples,
                seed=bootstrap_seed,
            )
            confidence_intervals[key][metric_name] = asdict(interval)
    retriever = {"name": "BM25", "k1": bm25_k1, "b": bm25_b}
    if retrieval_method == "hybrid":
        if rrf_constant is None:
            raise ValueError("Hybrid reports require an RRF rank constant.")
        if not embedding_model:
            raise ValueError("Hybrid reports require the embedding model name.")
        retriever = {
            "name": "BM25 + dense RRF",
            "k1": bm25_k1,
            "b": bm25_b,
            "rrf_constant": rrf_constant,
            "embedding_model": embedding_model,
        }
    elif retrieval_method == "bm25_prf":
        if feedback_document_count < 1 or feedback_term_count < 1:
            raise ValueError("Query feedback counts must be positive.")
        retriever = {
            "name": "BM25 + pseudo-relevance query expansion",
            "k1": bm25_k1,
            "b": bm25_b,
            "query_transformation": "rank_weighted_top_terms",
            "feedback_document_count": feedback_document_count,
            "feedback_term_count": feedback_term_count,
        }
    elif retrieval_method == "dense":
        if not embedding_model:
            raise ValueError("Dense reports require the embedding model name.")
        retriever = {"name": "Dense", "embedding_model": embedding_model}
    elif retrieval_method != "bm25":
        raise ValueError("retrieval_method must be 'bm25', 'dense', or 'hybrid'.")

    latency_values = sorted(item.retrieval_latency_ms for item in report.per_query)
    reranker = None
    if reranker_model is not None:
        if not reranker_model.strip() or reranker_candidate_count is None:
            raise ValueError("Reranker reports require a model and candidate count.")
        reranker = {
            "model": reranker_model,
            "candidate_count": reranker_candidate_count,
        }

    payload = {
        "report_schema_version": 2,
        "run_id": run_id,
        "dataset_version": dataset_version,
        "workspace_id": str(workspace_id),
        "split": report.split,
        "chunk_count": chunk_count,
        "evidence_overlap_threshold": evidence_overlap,
        "retriever": retriever,
        "reranker": reranker,
        "retrieval_latency_ms": {
            "p50": _percentile(latency_values, 0.50),
            "p95": _percentile(latency_values, 0.95),
            "query_count": len(latency_values),
        },
        "answerable_query_count": report.answerable_query_count,
        "excluded_unanswerable_query_count": report.excluded_unanswerable_query_count,
        "unanswerable_query_count": report.unanswerable_query_count,
        "unanswerable_empty_result_count": report.unanswerable_empty_result_count,
        "unanswerable_empty_result_rate": report.unanswerable_empty_result_rate,
        "k_values": report.k_values,
        "metrics_at_k": report.metrics_at_k,
        "confidence_intervals_at_k": confidence_intervals,
        "bootstrap": {
            "method": "percentile",
            "confidence_level": confidence_level,
            "resamples": bootstrap_resamples,
            "seed": bootstrap_seed,
        },
        "per_query": [
            {
                "query_id": item.query_id,
                "relevant_chunk_count": item.relevant_chunk_count,
                "retrieval_latency_ms": item.retrieval_latency_ms,
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
    confidence_intervals = payload["confidence_intervals_at_k"]
    assert isinstance(metrics_at_k, dict)
    assert isinstance(confidence_intervals, dict)
    bootstrap = payload["bootstrap"]
    assert isinstance(bootstrap, dict)
    retriever = payload["retriever"]
    assert isinstance(retriever, dict)
    latency = payload["retrieval_latency_ms"]
    assert isinstance(latency, dict)
    empty_result_rate = payload["unanswerable_empty_result_rate"]
    empty_result_text = (
        "not applicable" if empty_result_rate is None else f"{empty_result_rate:.1%}"
    )
    confidence_percent = bootstrap["confidence_level"] * 100
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
        f"- Unanswerable queries with no BM25 matches: "
        f"{payload['unanswerable_empty_result_count']} / "
        f"{payload['unanswerable_query_count']} ({empty_result_text})",
        f"- Evidence overlap threshold: {payload['evidence_overlap_threshold']}",
        f"- Retriever: `{retriever['name']}`",
        *(
            [f"- BM25 parameters: `k1={retriever['k1']}`, `b={retriever['b']}`"]
            if "k1" in retriever
            else []
        ),
        f"- Retrieval latency (model warm): p50 `{latency['p50']:.2f} ms`, "
        f"p95 `{latency['p95']:.2f} ms` across {latency['query_count']} queries",
        "",
        "The no-match rate measures whether BM25 returned any lexical matches. "
        "A returned match is not evidence that a passage answers the query.",
        "",
        "## Macro-averaged ranking metrics",
        "",
        "| k | Metric | Mean | Percentile confidence interval |",
        "| ---: | --- | ---: | ---: |",
    ]
    if "rrf_constant" in retriever:
        lines.insert(14, f"- RRF rank constant: `{retriever['rrf_constant']}`")
        lines.insert(15, f"- Embedding model: `{retriever['embedding_model']}`")
    if "query_transformation" in retriever:
        lines.insert(16, "- Query transformation: `rank-weighted top-term feedback`")
        lines.insert(
            17,
            f"- Feedback: `{retriever['feedback_document_count']}` chunks, "
            f"`{retriever['feedback_term_count']}` expansion terms",
        )
    reranker = payload["reranker"]
    if isinstance(reranker, dict):
        lines.insert(
            16,
            f"- Reranker: `{reranker['model']}` over "
            f"{reranker['candidate_count']} candidates",
        )
    for key, values in metrics_at_k.items():
        for metric_name, mean_value in values.items():
            interval = confidence_intervals[key][metric_name]
            lines.append(
                f"| {key} | {metric_name} | {mean_value:.4f} | "
                f"[{interval['lower']:.4f}, {interval['upper']:.4f}] |"
            )
    lines.extend(
        (
            "",
            f"Intervals use {bootstrap['resamples']} seeded percentile bootstrap "
            f"resamples (seed {bootstrap['seed']}, confidence "
            f"{confidence_percent:.1f}%).",
            "Confidence intervals from very small query sets are unstable; with one "
            "query the interval is degenerate. This report alone does not establish "
            "that one configuration is better than another.",
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


def _percentile(sorted_values: list[float], fraction: float) -> float:
    position = fraction * (len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight
