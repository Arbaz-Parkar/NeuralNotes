"""Ports implemented by document format adapters."""

from pathlib import Path
from typing import Protocol

from neuralnotes.parsers.models import ParsedDocument


class DocumentParser(Protocol):
    """Parse a supported document file into page-aware plain text."""

    def parse(self, source_path: Path) -> ParsedDocument:
        """Return document metadata and extracted text with source page numbers."""
