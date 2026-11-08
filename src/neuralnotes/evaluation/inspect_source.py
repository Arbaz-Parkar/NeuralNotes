"""Print cleaned source-page text with chunk-compatible character offsets."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from neuralnotes.cleaning import clean_document
from neuralnotes.downloader import load_manifest
from neuralnotes.parsers import PypdfDocumentParser
from neuralnotes.parsers.models import ParsedPage


def render_page_with_offsets(page: ParsedPage) -> str:
    """Render one page as lines labeled with zero-based end-exclusive offsets."""
    output = [
        (
            f"PDF page {page.page_number} — cleaned text length "
            f"{len(page.text)} characters"
        ),
        "Offsets are zero-based and end-exclusive; line breaks are not included.",
    ]
    cursor = 0
    for line in page.text.splitlines(keepends=True):
        content = line.removesuffix("\n").removesuffix("\r")
        end = cursor + len(content)
        output.append(f"[{cursor}:{end}] {content}")
        cursor += len(line)
    if not page.text:
        output.append("[0:0] <empty page>")
    return "\n".join(output)


def main(argv: Sequence[str] | None = None) -> int:
    """Read a manifest PDF and display the cleaned text for one page."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-id", required=True)
    parser.add_argument("--page-number", type=int, required=True)
    parser.add_argument(
        "--manifest", type=Path, default=Path("data/manifest/papers.json")
    )
    parser.add_argument("--pdf-dir", type=Path, default=Path("data/raw/acl_anthology"))
    args = parser.parse_args(argv)

    if args.page_number < 1:
        parser.error("--page-number must be at least 1")
    papers = load_manifest(args.manifest)
    paper = next((item for item in papers if item.anthology_id == args.paper_id), None)
    if paper is None:
        parser.error(f"Unknown paper id in manifest: {args.paper_id}")

    pdf_path = args.pdf_dir / f"{paper.anthology_id}.pdf"
    document = clean_document(PypdfDocumentParser().parse(pdf_path))
    if args.page_number > document.page_count:
        parser.error(
            f"Page {args.page_number} is outside this PDF's "
            f"1-{document.page_count} range"
        )

    page = document.pages[args.page_number - 1]
    print(f"Paper: {paper.anthology_id} — {document.title or paper.title}")
    print(render_page_with_offsets(page))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
