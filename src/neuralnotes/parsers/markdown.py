"""Markdown document parser adapter."""

import re
from pathlib import Path

from neuralnotes.parsers.models import ParsedDocument
from neuralnotes.parsers.text import PlainTextDocumentParser

_ATX_H1_PATTERN = re.compile(r"^ {0,3}#(?!#)\s+(.+?)\s*#*\s*$")
_FENCE_PATTERN = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def _extract_first_h1(markdown_text: str) -> str | None:
    """Return the first level-one ATX heading outside a fenced code block."""
    fence_character: str | None = None
    fence_length = 0

    for line in markdown_text.splitlines():
        if fence_character is not None:
            closing_fence = re.match(
                rf"^ {{0,3}}{re.escape(fence_character)}{{{fence_length},}}\s*$",
                line,
            )
            if closing_fence:
                fence_character = None
            continue

        fence_match = _FENCE_PATTERN.match(line)
        if fence_match:
            fence = fence_match.group(1)
            fence_character = fence[0]
            fence_length = len(fence)
            continue

        heading_match = _ATX_H1_PATTERN.match(line)
        if heading_match:
            title = heading_match.group(1).strip()
            return title or None

    return None


class MarkdownDocumentParser:
    """Read Markdown as one page and use its first level-one heading as title."""

    def parse(self, source_path: Path) -> ParsedDocument:
        document = PlainTextDocumentParser().parse(source_path)
        title = _extract_first_h1(document.pages[0].text)
        return ParsedDocument(
            source_path=document.source_path,
            title=title,
            author=None,
            pages=document.pages,
        )
