"""Workspace-scoped ingestion statistics and Markdown report generation."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from statistics import median
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from neuralnotes.chunking import ChunkStrategy
from neuralnotes.database import (
    create_database_engine,
    create_database_session_factory,
)
from neuralnotes.db.models import Chunk, Document

_STRATEGIES: tuple[ChunkStrategy, ...] = (
    "fixed_size",
    "recursive",
    "sentence_window",
)


@dataclass(frozen=True, slots=True)
class TokenDistribution:
    """Summary of token counts per stored chunk."""

    minimum: int | None
    median: float | None
    percentile_95: int | None
    mean: float | None
    maximum: int | None


@dataclass(frozen=True, slots=True)
class IngestionStatistics:
    """Workspace document, strategy, and chunk-length totals."""

    workspace_id: UUID
    ready_document_count: int
    chunk_count: int
    chunks_by_strategy: tuple[tuple[str, int], ...]
    token_distribution: TokenDistribution


def collect_ingestion_statistics(
    session: Session,
    workspace_id: UUID,
) -> IngestionStatistics:
    """Aggregate ready-document chunk counts for one workspace."""
    ready_document_filter = and_(
        Document.workspace_id == workspace_id,
        Document.status == "ready",
    )
    ready_document_count = (
        session.scalar(
            select(func.count()).select_from(Document).where(ready_document_filter)
        )
        or 0
    )
    ready_chunk_scope = (
        Chunk.workspace_id == Document.workspace_id,
        Chunk.document_id == Document.id,
        Document.workspace_id == workspace_id,
        Document.status == "ready",
    )
    strategy_counts = dict(
        session.execute(
            select(Chunk.strategy, func.count())
            .join(Document, and_(*ready_chunk_scope))
            .group_by(Chunk.strategy)
        ).all()
    )
    token_counts = sorted(
        session.scalars(
            select(Chunk.token_count)
            .join(Document, and_(*ready_chunk_scope))
            .order_by(Chunk.token_count)
        ).all()
    )
    chunks_by_strategy = tuple(
        (strategy, int(strategy_counts.get(strategy, 0))) for strategy in _STRATEGIES
    )
    distribution = _summarize_tokens(token_counts)
    return IngestionStatistics(
        workspace_id=workspace_id,
        ready_document_count=int(ready_document_count),
        chunk_count=len(token_counts),
        chunks_by_strategy=chunks_by_strategy,
        token_distribution=distribution,
    )


def _summarize_tokens(token_counts: list[int]) -> TokenDistribution:
    if not token_counts:
        return TokenDistribution(None, None, None, None, None)
    percentile_index = max(0, ceil(0.95 * len(token_counts)) - 1)
    return TokenDistribution(
        minimum=token_counts[0],
        median=float(median(token_counts)),
        percentile_95=token_counts[percentile_index],
        mean=sum(token_counts) / len(token_counts),
        maximum=token_counts[-1],
    )


def render_statistics_markdown(statistics: IngestionStatistics) -> str:
    """Render deterministic workspace statistics as Markdown."""
    distribution = statistics.token_distribution
    lines = [
        f"# Ingestion statistics — workspace `{statistics.workspace_id}`",
        "",
        f"- Ready documents: {statistics.ready_document_count}",
        f"- Chunks: {statistics.chunk_count}",
        "",
        "## Chunks by strategy",
        "",
        "| Strategy | Chunks |",
        "| --- | ---: |",
    ]
    lines.extend(
        f"| `{strategy}` | {count} |"
        for strategy, count in statistics.chunks_by_strategy
    )
    lines.extend(("", "## Token counts per chunk", ""))
    if distribution.minimum is None:
        lines.append("No chunks are stored in this workspace yet.")
    else:
        lines.extend(
            (
                f"- Minimum: {distribution.minimum}",
                f"- Median: {distribution.median:.1f}",
                f"- 95th percentile: {distribution.percentile_95}",
                f"- Mean: {distribution.mean:.1f}",
                f"- Maximum: {distribution.maximum}",
            )
        )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Print or save a workspace's ingestion statistics report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace-id",
        type=UUID,
        required=True,
        help="Workspace UUID to summarize.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional Markdown output path; otherwise print the report.",
    )
    args = parser.parse_args(argv)

    engine = create_database_engine()
    try:
        session_factory = create_database_session_factory(engine)
        with session_factory() as session:
            statistics = collect_ingestion_statistics(session, args.workspace_id)
    finally:
        engine.dispose()

    report = render_statistics_markdown(statistics)
    if args.output is None:
        print(report, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote ingestion statistics to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
