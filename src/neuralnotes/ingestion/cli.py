"""Ingest one license-checked ACL Anthology paper into the local database."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import UUID

from neuralnotes.chunking import FixedSizeChunker, HuggingFaceOffsetTokenizer
from neuralnotes.database import (
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
from neuralnotes.embeddings import SentenceTransformerEmbedder
from neuralnotes.ingestion.pipeline import DocumentIngestionPipeline
from neuralnotes.logging_config import configure_logging
from neuralnotes.parsers import PypdfDocumentParser
from neuralnotes.settings import Settings

LOGGER = logging.getLogger(__name__)
DEFAULT_WORKSPACE_ID = UUID("11111111-1111-4111-8111-111111111111")
DEFAULT_WORKSPACE_NAME = "NeuralNotes local"


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """Summary of one document saved to a workspace."""

    document_id: str
    workspace_id: UUID
    title: str | None
    page_count: int
    chunk_count: int


def _build_pipeline() -> DocumentIngestionPipeline:
    """Create the initial local PDF, tokenizer, chunker, and embedding stack."""
    tokenizer = HuggingFaceOffsetTokenizer.from_pretrained()
    return DocumentIngestionPipeline(
        parser=PypdfDocumentParser(),
        chunker=FixedSizeChunker(tokenizer),
        embedder=SentenceTransformerEmbedder(),
    )


def _find_paper(papers: Sequence[Paper], paper_id: str) -> Paper:
    for paper in papers:
        if paper.anthology_id == paper_id:
            return paper
    raise ValueError(f"Paper id is not present in the verified manifest: {paper_id}")


def ingest_paper(
    paper_id: str,
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    pdf_dir: Path = DEFAULT_OUTPUT_DIR,
    workspace_id: UUID = DEFAULT_WORKSPACE_ID,
    workspace_name: str = DEFAULT_WORKSPACE_NAME,
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

    prepared = _build_pipeline().prepare(source_path, document_id=paper.anthology_id)
    engine = create_database_engine(settings)
    try:
        session_factory = create_database_session_factory(engine)
        with session_factory.begin() as session:
            workspace = session.get(Workspace, workspace_id)
            if workspace is None:
                session.add(Workspace(id=workspace_id, name=workspace_name))
                session.flush()

            persist_prepared_document(
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
    finally:
        engine.dispose()

    return IngestionResult(
        document_id=paper.anthology_id,
        workspace_id=workspace_id,
        title=prepared.title,
        page_count=prepared.page_count,
        chunk_count=len(prepared.chunks),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run one-paper ingestion from PowerShell or another command shell."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paper-id",
        required=True,
        help="ACL Anthology ID from data/manifest/papers.json.",
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
    args = parser.parse_args(argv)

    configure_logging()
    try:
        result = ingest_paper(
            args.paper_id,
            manifest_path=args.manifest,
            pdf_dir=args.pdf_dir,
            workspace_id=args.workspace_id,
            workspace_name=args.workspace_name,
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
