"""Run a workspace-scoped BM25 evaluation over a verified JSONL split."""

import argparse
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from neuralnotes.database import (
    create_database_engine,
    create_database_session_factory,
)
from neuralnotes.db.retrieval import load_workspace_chunks
from neuralnotes.evaluation.dataset import load_cases
from neuralnotes.evaluation.reports import write_evaluation_reports
from neuralnotes.evaluation.runner import evaluate_retrieval
from neuralnotes.retrieval import BM25Index


def main(argv: Sequence[str] | None = None) -> int:
    """Load one verified split, score BM25, and write versioned reports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--split", choices=("dev", "test"), required=True)
    parser.add_argument("--workspace-id", type=UUID, required=True)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/processed/evaluations")
    )
    parser.add_argument("--k-values", type=int, nargs="+", default=(5, 10, 20))
    parser.add_argument("--evidence-overlap", type=float, default=0.5)
    parser.add_argument("--k1", type=float, default=1.5)
    parser.add_argument("--b", type=float, default=0.75)
    args = parser.parse_args(argv)

    cases = load_cases(args.dataset, split=args.split)
    engine = create_database_engine()
    try:
        session_factory = create_database_session_factory(engine)
        with session_factory() as session:
            chunks = load_workspace_chunks(session, args.workspace_id)
    finally:
        engine.dispose()

    index = BM25Index(chunks, k1=args.k1, b=args.b)

    def retrieve(query: str, top_k: int) -> tuple[str, ...]:
        return tuple(hit.chunk.chunk_id for hit in index.search(query, top_k=top_k))

    report = evaluate_retrieval(
        cases,
        chunks,
        retrieve,
        k_values=tuple(args.k_values),
        minimum_evidence_overlap=args.evidence_overlap,
    )
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    json_path, markdown_path = write_evaluation_reports(
        report,
        args.output_dir,
        dataset_version=args.dataset_version,
        workspace_id=args.workspace_id,
        run_id=run_id,
        evidence_overlap=args.evidence_overlap,
        bm25_k1=args.k1,
        bm25_b=args.b,
        chunk_count=len(chunks),
    )
    print(f"Wrote evaluation JSON to {json_path}")
    print(f"Wrote evaluation Markdown to {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
