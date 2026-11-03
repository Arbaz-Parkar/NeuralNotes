"""Deterministic text cleanup that preserves page and line structure."""

import re
from dataclasses import dataclass
from typing import Literal

from neuralnotes.parsers.models import ParsedDocument, ParsedPage


@dataclass(frozen=True, slots=True)
class RepeatedMarginLine:
    """A top or bottom page line that recurs across multiple pages."""

    location: Literal["top", "bottom"]
    text: str
    page_numbers: tuple[int, ...]


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


def find_repeated_margin_lines(
    document: ParsedDocument,
    *,
    margin_line_count: int = 3,
    minimum_pages: int = 2,
) -> tuple[RepeatedMarginLine, ...]:
    """Find repeated top or bottom lines for review, without removing text."""
    if margin_line_count < 1:
        raise ValueError("margin_line_count must be at least 1.")
    if minimum_pages < 2:
        raise ValueError("minimum_pages must be at least 2.")

    matches: dict[tuple[str, str], tuple[str, set[int]]] = {}
    for page in document.pages:
        lines = [
            line.strip()
            for line in clean_page_text(page.text).splitlines()
            if line.strip()
        ]
        margins = {
            "top": lines[:margin_line_count],
            "bottom": lines[-margin_line_count:],
        }
        for location, margin_lines in margins.items():
            for line in margin_lines:
                normalized = re.sub(r"\d+", "<number>", line.casefold())
                key = (location, normalized)
                if key not in matches:
                    matches[key] = (line, set())
                matches[key][1].add(page.page_number)

    candidates = [
        RepeatedMarginLine(
            location=location,
            text=text,
            page_numbers=tuple(sorted(pages)),
        )
        for (location, _), (text, pages) in matches.items()
        if len(pages) >= minimum_pages
    ]
    return tuple(
        sorted(candidates, key=lambda item: (item.location, item.text.casefold()))
    )
