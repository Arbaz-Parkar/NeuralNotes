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
from neuralnotes.db.retrieval import (
    get_workspace_embedding_model,
    load_workspace_chunk_embeddings,
    load_workspace_chunks,
)
from neuralnotes.embeddings import SentenceTransformerEmbedder
from neuralnotes.evaluation.dataset import load_cases
from neuralnotes.evaluation.reports import write_evaluation_reports
from neuralnotes.evaluation.runner import evaluate_retrieval
from neuralnotes.retrieval import BM25Index, DenseIndex, reciprocal_rank_fusion


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
    parser.add_argument(
        "--retrieval-method",
        choices=("bm25", "hybrid"),
        default="bm25",
        help="Evaluate lexical BM25 or BM25+dense reciprocal-rank fusion.",
    )
    parser.add_argument("--rrf-constant", type=float, default=60.0)
    parser.add_argument("--confidence-level", type=float, default=0.95)
    parser.add_argument("--bootstrap-resamples", type=int, default=2_000)
    parser.add_argument("--bootstrap-seed", type=int, default=0)
    args = parser.parse_args(argv)

    cases = load_cases(args.dataset, split=args.split)
    engine = create_database_engine()
    try:
        session_factory = create_database_session_factory(engine)
        with session_factory() as session:
            chunks = load_workspace_chunks(session, args.workspace_id)
            embedded_chunks = (
                load_workspace_chunk_embeddings(session, args.workspace_id)
                if args.retrieval_method == "hybrid"
                else ()
            )
            embedding_model = (
                get_workspace_embedding_model(session, args.workspace_id)
                if args.retrieval_method == "hybrid"
                else None
            )
    finally:
        engine.dispose()

    if args.retrieval_method == "hybrid" and (
        not embedded_chunks or embedding_model is None
    ):
        raise ValueError(
            "Hybrid retrieval requires stored chunk embeddings and a model."
        )

    index = BM25Index(chunks, k1=args.k1, b=args.b)
    dense_index = DenseIndex(embedded_chunks) if embedded_chunks else None
    embedder = (
        SentenceTransformerEmbedder(model_name=embedding_model)
        if dense_index is not None and embedding_model is not None
        else None
    )
    candidate_k = min(max(args.k_values) * 5, len(chunks))

    def retrieve(query: str, top_k: int) -> tuple[str, ...]:
        if dense_index is None or embedder is None:
            return tuple(hit.chunk.chunk_id for hit in index.search(query, top_k=top_k))
        lexical_ids = tuple(
            hit.chunk.chunk_id for hit in index.search(query, top_k=candidate_k)
        )
        dense_ids = tuple(
            hit.chunk.chunk_id
            for hit in dense_index.search(
                embedder.embed_query(query), top_k=candidate_k
            )
        )
        fused = reciprocal_rank_fusion(
            (lexical_ids, dense_ids),
            rank_constant=args.rrf_constant,
            top_k=top_k,
        )
        return tuple(hit.chunk_id for hit in fused)

    def retrieve_lexical(query: str, top_k: int) -> tuple[str, ...]:
        return tuple(hit.chunk.chunk_id for hit in index.search(query, top_k=top_k))

    report = evaluate_retrieval(
        cases,
        chunks,
        retrieve,
        k_values=tuple(args.k_values),
        minimum_evidence_overlap=args.evidence_overlap,
        unanswerable_retrieve=retrieve_lexical,
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
        retrieval_method=args.retrieval_method,
        rrf_constant=args.rrf_constant if args.retrieval_method == "hybrid" else None,
        embedding_model=embedding_model,
        chunk_count=len(chunks),
        confidence_level=args.confidence_level,
        bootstrap_resamples=args.bootstrap_resamples,
        bootstrap_seed=args.bootstrap_seed,
    )
    print(f"Wrote evaluation JSON to {json_path}")
    print(f"Wrote evaluation Markdown to {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
