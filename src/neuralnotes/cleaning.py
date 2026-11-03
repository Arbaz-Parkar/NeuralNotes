"""Deterministic text cleanup that preserves page and line structure."""

import re

from neuralnotes.parsers.models import ParsedDocument, ParsedPage


def clean_page_text(text: str) -> str:
    """Normalize line endings, horizontal spacing, and repeated blank lines."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned_lines: list[str] = []

    for raw_line in normalized.split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line:
            if cleaned_lines and cleaned_lines[-1]:
                cleaned_lines.append("")
            continue
        cleaned_lines.append(line)

    while cleaned_lines and not cleaned_lines[-1]:
        cleaned_lines.pop()

    return "\n".join(cleaned_lines)


def clean_document(document: ParsedDocument) -> ParsedDocument:
    """Return a cleaned copy while preserving document metadata and page ids."""
    pages = tuple(
        ParsedPage(page_number=page.page_number, text=clean_page_text(page.text))
        for page in document.pages
    )
    return ParsedDocument(
        source_path=document.source_path,
        title=document.title,
        author=document.author,
        pages=pages,
    )
