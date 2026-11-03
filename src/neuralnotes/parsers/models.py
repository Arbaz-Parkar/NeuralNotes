"""Parsed document types shared by ingestion adapters."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ParsedPage:
    """Text extracted from one one-based source page."""

    page_number: int
    text: str

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("Page numbers start at 1.")


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Extracted text and basic document metadata, before cleaning or chunking."""

    source_path: Path
    title: str | None
    author: str | None
    pages: tuple[ParsedPage, ...]

    def __post_init__(self) -> None:
        expected_page_numbers = tuple(range(1, len(self.pages) + 1))
        actual_page_numbers = tuple(page.page_number for page in self.pages)
        if actual_page_numbers != expected_page_numbers:
            raise ValueError(
                "Parsed document pages must be numbered sequentially from 1."
            )

    @property
    def page_count(self) -> int:
        """Return the number of parsed source pages."""
        return len(self.pages)
