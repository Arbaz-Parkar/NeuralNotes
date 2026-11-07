"""Ingest one license-checked ACL Anthology paper into the local database."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from neuralnotes.chunking import (
    Chunker,
    ChunkStrategy,
    FixedSizeChunker,
    HuggingFaceOffsetTokenizer,
    RecursiveChunker,
    SentenceWindowChunker,
    TokenSpanTokenizer,
)
from neuralnotes.database import (
    check_database_connection,
    create_database_engine,
    create_database_session_factory,
)
from neuralnotes.db import Workspace
from neuralnotes.db.persistence import persist_prepared_document
from neuralnotes.downloader import (
    DEFAULT_MANIFEST,
    DEFAULT_OUTPUT_DIR,
    Paper,
    load_manifest,
)
from neuralnotes.embeddings import CachedEmbeddingModel, SentenceTransformerEmbedder
from neuralnotes.ingestion.pipeline import DocumentIngestionPipeline, PreparedDocument
from neuralnotes.logging_config import configure_logging
from neuralnotes.parsers import PypdfDocumentParser
from neuralnotes.settings import Settings

LOGGER = logging.getLogger(__name__)
DEFAULT_WORKSPACE_ID = UUID("11111111-1111-4111-8111-111111111111")
DEFAULT_WORKSPACE_NAME = "NeuralNotes local"
CHUNKING_STRATEGIES: tuple[ChunkStrategy, ...] = (
    "fixed_size",
    "recursive",
    "sentence_window",
)


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """Summary of one document saved to a workspace."""

    document_id: str
    workspace_id: UUID
    title: str | None
    page_count: int
    chunk_count: int


@dataclass(frozen=True, slots=True)
class IngestionFailure:
    """Paper identifier and error text for one failed batch item."""

    document_id: str
    error: str


@dataclass(frozen=True, slots=True)
class BatchIngestionResult:
    """Successful and failed results from a manifest ingestion run."""

    ingested: tuple[IngestionResult, ...]
    failures: tuple[IngestionFailure, ...]


def _build_chunker(
    tokenizer: TokenSpanTokenizer,
    strategy: ChunkStrategy,
) -> Chunker:
    """Create the selected page-aware chunking strategy."""
    if strategy == "fixed_size":
        return FixedSizeChunker(tokenizer)
    if strategy == "recursive":
        return RecursiveChunker(tokenizer)
    if strategy == "sentence_window":
        return SentenceWindowChunker(tokenizer)
    raise ValueError(f"Unsupported chunking strategy: {strategy}.")


def _build_pipeline(
    chunking_strategy: ChunkStrategy = "fixed_size",
) -> DocumentIngestionPipeline:
    """Create the local PDF, tokenizer, selected chunker, and embedder stack."""
    tokenizer = HuggingFaceOffsetTokenizer.from_pretrained()
    return DocumentIngestionPipeline(
        parser=PypdfDocumentParser(),
        chunker=_build_chunker(tokenizer, chunking_strategy),
        embedder=CachedEmbeddingModel(SentenceTransformerEmbedder()),
    )


def _find_paper(papers: Sequence[Paper], paper_id: str) -> Paper:
    for paper in papers:
        if paper.anthology_id == paper_id:
            return paper
    raise ValueError(f"Paper id is not present in the verified manifest: {paper_id}")


def _save_prepared_document(
    session_factory: sessionmaker[Session],
    paper: Paper,
    prepared: PreparedDocument,
    *,
    workspace_id: UUID,
    workspace_name: str,
) -> IngestionResult:
    with session_factory.begin() as session:
        workspace = session.get(Workspace, workspace_id)
        if workspace is None:
            session.add(Workspace(id=workspace_id, name=workspace_name))
            session.flush()

        document = persist_prepared_document(
            session,
            prepared,
            workspace_id=workspace_id,
            mime_type="application/pdf",
            source_url=paper.landing_page_url,
            pdf_url=paper.pdf_url,
            year=paper.year,
            license_name=paper.license,
            license_url=paper.license_url,
            license_evidence_url=paper.license_evidence_url,
            license_verified_on=date.fromisoformat(paper.license_verified_on),
        )

    return IngestionResult(
        document_id=document.id,
        workspace_id=workspace_id,
        title=document.title,
        page_count=prepared.page_count,
        chunk_count=len(prepared.chunks),
    )


def ingest_paper(
    paper_id: str,
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    pdf_dir: Path = DEFAULT_OUTPUT_DIR,
    workspace_id: UUID = DEFAULT_WORKSPACE_ID,
    workspace_name: str = DEFAULT_WORKSPACE_NAME,
    chunking_strategy: ChunkStrategy = "fixed_size",
    settings: Settings | None = None,
) -> IngestionResult:
    """Prepare and persist one paper selected from the verified manifest."""
    if not paper_id.strip():
        raise ValueError("paper_id must not be empty.")
    if not workspace_name.strip():
        raise ValueError("workspace_name must not be empty.")

    paper = _find_paper(load_manifest(manifest_path), paper_id)
    source_path = pdf_dir / f"{paper.anthology_id}.pdf"
    if not source_path.is_file():
        raise FileNotFoundError(
            f"Local PDF not found: {source_path}. Run neuralnotes.downloader first."
        )

    prepared = _build_pipeline(chunking_strategy).prepare(
        source_path, document_id=paper.anthology_id
    )
    engine = create_database_engine(settings)
    try:
        session_factory = create_database_session_factory(engine)
        result = _save_prepared_document(
            session_factory,
            paper,
            prepared,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
        )
    finally:
        engine.dispose()

    return result


def ingest_manifest(
    *,
    paper_ids: Sequence[str] | None = None,
    manifest_path: Path = DEFAULT_MANIFEST,
    pdf_dir: Path = DEFAULT_OUTPUT_DIR,
    workspace_id: UUID = DEFAULT_WORKSPACE_ID,
    workspace_name: str = DEFAULT_WORKSPACE_NAME,
    chunking_strategy: ChunkStrategy = "fixed_size",
    settings: Settings | None = None,
) -> BatchIngestionResult:
    """Process selected or all manifest papers one at a time.

    The parser, embedding model, SQLite cache, engine, and session factory are
    reused for the run. Each paper is prepared in memory and persisted in its
    own transaction so one bad source does not roll back completed imports.
    """
    if not workspace_name.strip():
        raise ValueError("workspace_name must not be empty.")

    papers = load_manifest(manifest_path)
    if paper_ids is None:
        selected_papers = iter(papers)
    else:
        requested_ids = tuple(paper_ids)
        if not requested_ids:
            raise ValueError("At least one paper id must be selected.")
        if len(requested_ids) != len(set(requested_ids)):
            raise ValueError("Paper ids must not contain duplicates.")
        manifest_by_id = {paper.anthology_id: paper for paper in papers}
        unknown_ids = tuple(
            paper_id for paper_id in requested_ids if paper_id not in manifest_by_id
        )
        if unknown_ids:
            raise ValueError(
                "Paper ids are not present in the verified manifest: "
                f"{', '.join(unknown_ids)}"
            )
        selected_papers = (manifest_by_id[paper_id] for paper_id in requested_ids)

    engine = create_database_engine(settings)
    ingested: list[IngestionResult] = []
    failures: list[IngestionFailure] = []
    try:
        check_database_connection(engine)
        pipeline = _build_pipeline(chunking_strategy)
        session_factory = create_database_session_factory(engine)

        for paper in selected_papers:
            try:
                source_path = pdf_dir / f"{paper.anthology_id}.pdf"
                if not source_path.is_file():
                    raise FileNotFoundError(
                        f"Local PDF not found: {source_path}. "
                        "Run neuralnotes.downloader first."
                    )
                prepared = pipeline.prepare(source_path, document_id=paper.anthology_id)
                result = _save_prepared_document(
                    session_factory,
                    paper,
                    prepared,
                    workspace_id=workspace_id,
                    workspace_name=workspace_name,
                )
            except Exception as exc:
                failures.append(
                    IngestionFailure(document_id=paper.anthology_id, error=str(exc))
                )
                LOGGER.exception("Ingestion failed for paper %s", paper.anthology_id)
            else:
                ingested.append(result)
                LOGGER.info(
                    "Ingested %s: %d pages, %d chunks",
                    result.document_id,
                    result.page_count,
                    result.chunk_count,
                )
    finally:
        engine.dispose()

    return BatchIngestionResult(
        ingested=tuple(ingested),
        failures=tuple(failures),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run one-paper or manifest-batch ingestion from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--paper-id",
        action="append",
        help="Verified ACL Anthology ID; repeat to ingest selected papers.",
    )
    selection.add_argument(
        "--all",
        action="store_true",
        help="Ingest every paper in the verified manifest.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to the verified ACL Anthology manifest.",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Folder containing downloaded ACL PDFs.",
    )
    parser.add_argument(
        "--workspace-id",
        type=UUID,
        default=DEFAULT_WORKSPACE_ID,
        help=f"Workspace UUID (default: {DEFAULT_WORKSPACE_ID}).",
    )
    parser.add_argument(
        "--workspace-name",
        default=DEFAULT_WORKSPACE_NAME,
        help=(
            "Name used if the workspace is created "
            f"(default: {DEFAULT_WORKSPACE_NAME})."
        ),
    )
    parser.add_argument(
        "--chunking-strategy",
        choices=CHUNKING_STRATEGIES,
        default="fixed_size",
        help="Chunking strategy to store (default: fixed_size).",
    )
    args = parser.parse_args(argv)

    configure_logging()
    try:
        if args.all or len(args.paper_id) > 1:
            result = ingest_manifest(
                paper_ids=None if args.all else args.paper_id,
                manifest_path=args.manifest,
                pdf_dir=args.pdf_dir,
                workspace_id=args.workspace_id,
                workspace_name=args.workspace_name,
                chunking_strategy=args.chunking_strategy,
            )
            chunk_count = sum(item.chunk_count for item in result.ingested)
            LOGGER.info(
                "Finished batch ingestion: %d succeeded, %d failed, %d chunks",
                len(result.ingested),
                len(result.failures),
                chunk_count,
            )
            return 1 if result.failures else 0

        result = ingest_paper(
            args.paper_id[0],
            manifest_path=args.manifest,
            pdf_dir=args.pdf_dir,
            workspace_id=args.workspace_id,
            workspace_name=args.workspace_name,
            chunking_strategy=args.chunking_strategy,
        )
    except Exception:
        LOGGER.exception("Ingestion failed for paper %s", args.paper_id)
        return 1

    LOGGER.info(
        "Ingested %s into workspace %s: %d pages, %d chunks",
        result.document_id,
        result.workspace_id,
        result.page_count,
        result.chunk_count,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
