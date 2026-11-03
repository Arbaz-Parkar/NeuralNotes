"""Compare two PDF text extractors on a small, fixed paper sample."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import platform
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from neuralnotes.downloader import load_manifest

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "raw" / "acl_anthology"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "parser_comparison"
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "manifest" / "papers.json"

# A small cross-section of the corpus: an early dense-retrieval paper, newer
# retrieval work, an evaluation paper, a domain benchmark, and graph retrieval.
SAMPLE_PAPER_IDS = (
    "2020.emnlp-main.550",
    "2024.emnlp-main.845",
    "2024.eacl-demo.16",
    "2024.findings-acl.372",
    "2025.findings-acl.624",
)

PARSER_NAMES = ("pypdf", "pdfplumber")
MANUAL_REVIEW_FIELDS = (
    "two_column_order_1_to_5",
    "equation_readability_1_to_5",
    "table_text_and_order_1_to_5",
    "section_flow_1_to_5",
    "notes",
)


def summarize_pages(page_texts: Sequence[str]) -> dict[str, int]:
    """Return basic extraction counts without treating them as quality scores."""
    combined_text = "\n".join(page_texts)
    return {
        "page_count": len(page_texts),
        "empty_pages": sum(not page.strip() for page in page_texts),
        "characters": sum(len(page) for page in page_texts),
        "words": sum(len(page.split()) for page in page_texts),
        "replacement_characters": combined_text.count("\ufffd"),
        "control_characters": sum(
            ord(character) < 32 and character not in "\n\r\t\f"
            for character in combined_text
        ),
    }


def _extract_with_pypdf(pdf_path: Path) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    return [page.extract_text() or "" for page in reader.pages]


def _extract_with_pdfplumber(pdf_path: Path) -> list[str]:
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def _package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"


def _write_extracted_text(path: Path, page_texts: Sequence[str]) -> None:
    page_sections = [
        f"===== PDF page {page_number} =====\n{text}"
        for page_number, text in enumerate(page_texts, start=1)
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n\n".join(page_sections), encoding="utf-8")


def _write_manual_review_template(path: Path) -> None:
    if path.exists():
        return

    fieldnames = ("paper_id", "parser", *MANUAL_REVIEW_FIELDS)
    with path.open("w", encoding="utf-8", newline="") as review_file:
        writer = csv.DictWriter(review_file, fieldnames=fieldnames)
        writer.writeheader()
        for paper_id in SAMPLE_PAPER_IDS:
            for parser_name in PARSER_NAMES:
                writer.writerow({"paper_id": paper_id, "parser": parser_name})


def _run_parser(parser_name: str, pdf_path: Path) -> tuple[list[str], float, str]:
    extract = {
        "pypdf": _extract_with_pypdf,
        "pdfplumber": _extract_with_pdfplumber,
    }[parser_name]
    started_at = time.perf_counter()
    page_texts = extract(pdf_path)
    elapsed_seconds = time.perf_counter() - started_at
    return page_texts, elapsed_seconds, _package_version(parser_name)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare pypdf and pdfplumber on five manifest papers. "
            "Extracted text and reports stay in ignored local data storage."
        )
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the comparison and write local reports for human review."""
    args = _parse_args(argv)
    try:
        papers = {paper.anthology_id: paper for paper in load_manifest(args.manifest)}
    except (OSError, ValueError) as exc:
        LOGGER.error("Could not load parser comparison manifest: %s", exc)
        return 2

    missing_records = [
        paper_id for paper_id in SAMPLE_PAPER_IDS if paper_id not in papers
    ]
    if missing_records:
        LOGGER.error("Sample papers are missing from the manifest: %s", missing_records)
        return 2

    missing_pdfs = [
        paper_id
        for paper_id in SAMPLE_PAPER_IDS
        if not (args.input_dir / f"{paper_id}.pdf").is_file()
    ]
    if missing_pdfs:
        LOGGER.error(
            "Download the sample PDFs first; missing from %s: %s",
            args.input_dir,
            missing_pdfs,
        )
        return 2

    results: list[dict[str, Any]] = []
    failures = 0
    for paper_id in SAMPLE_PAPER_IDS:
        paper = papers[paper_id]
        pdf_path = args.input_dir / f"{paper_id}.pdf"
        for parser_name in PARSER_NAMES:
            result: dict[str, Any] = {
                "paper_id": paper_id,
                "title": paper.title,
                "parser": parser_name,
            }
            try:
                page_texts, elapsed_seconds, parser_version = _run_parser(
                    parser_name, pdf_path
                )
                text_path = args.output_dir / "text" / parser_name / f"{paper_id}.txt"
                _write_extracted_text(text_path, page_texts)
                result.update(summarize_pages(page_texts))
                result["elapsed_seconds"] = round(elapsed_seconds, 4)
                result["version"] = parser_version
                result["text_file"] = str(text_path)
                LOGGER.info(
                    "%s %s: %d pages, %d words, %.2f seconds",
                    parser_name,
                    paper_id,
                    result["page_count"],
                    result["words"],
                    elapsed_seconds,
                )
            except Exception as exc:  # Record one parser failure and continue.
                failures += 1
                result["error"] = f"{type(exc).__name__}: {exc}"
                LOGGER.exception("%s failed on %s", parser_name, paper_id)
            results.append(result)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "python_version": platform.python_version(),
        "sample_paper_ids": list(SAMPLE_PAPER_IDS),
        "extraction_modes": {
            "pypdf": "PageObject.extract_text() default mode",
            "pdfplumber": "Page.extract_text() default mode",
        },
        "results": results,
        "note": (
            "Counts and timings describe extraction output; they are not quality "
            "scores. Use the text files and manual review sheet to judge layout, "
            "equations, and table reading order."
        ),
    }
    report_path = args.output_dir / "summary.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _write_manual_review_template(args.output_dir / "manual_review.csv")
    LOGGER.info("Comparison reports written under %s", args.output_dir)
    return 1 if failures else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
