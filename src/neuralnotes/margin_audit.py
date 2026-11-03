"""Report recurring page-margin lines from the local paper corpus."""

from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path
from typing import Any

from neuralnotes.cleaning import find_repeated_margin_lines
from neuralnotes.downloader import load_manifest
from neuralnotes.parsers import PypdfDocumentParser

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "manifest" / "papers.json"
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "raw" / "acl_anthology"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "margin_candidates.csv"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Find recurring top and bottom lines in local PDFs. "
            "The report is for review; it does not remove text."
        )
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--margin-lines", type=int, default=3)
    parser.add_argument("--minimum-pages", type=int, default=2)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Write a CSV of repeated margin-line candidates for manual review."""
    args = _parse_args(argv)
    if args.margin_lines < 1 or args.minimum_pages < 2:
        LOGGER.error(
            "Margin lines must be positive and minimum pages must be at least 2."
        )
        return 2

    try:
        papers = load_manifest(args.manifest)
    except (OSError, ValueError) as exc:
        LOGGER.error("Could not load paper manifest: %s", exc)
        return 2

    parser = PypdfDocumentParser()
    rows: list[dict[str, Any]] = []
    failures = 0
    for paper in papers:
        pdf_path = args.input_dir / f"{paper.anthology_id}.pdf"
        try:
            document = parser.parse(pdf_path)
        except Exception as exc:
            failures += 1
            LOGGER.error("Could not inspect %s: %s", paper.anthology_id, exc)
            continue

        for candidate in find_repeated_margin_lines(
            document,
            margin_line_count=args.margin_lines,
            minimum_pages=args.minimum_pages,
        ):
            rows.append(
                {
                    "paper_id": paper.anthology_id,
                    "title": paper.title,
                    "page_count": document.page_count,
                    "location": candidate.location,
                    "repeat_count": len(candidate.page_numbers),
                    "page_numbers": ",".join(map(str, candidate.page_numbers)),
                    "line_example": candidate.text,
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = (
        "paper_id",
        "title",
        "page_count",
        "location",
        "repeat_count",
        "page_numbers",
        "line_example",
    )
    with args.output.open("w", encoding="utf-8", newline="") as report_file:
        writer = csv.DictWriter(report_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    LOGGER.info("Wrote %d repeated-margin candidates to %s", len(rows), args.output)
    return 1 if failures else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
