"""PDF parser adapter backed by pypdf."""

from pathlib import Path

from pypdf import PdfReader

from neuralnotes.errors import DocumentParseError, ResourceNotFoundError
from neuralnotes.parsers.models import ParsedDocument, ParsedPage


def _normalize_metadata_value(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


class PypdfDocumentParser:
    """Extract page text and basic metadata from a PDF without modifying text."""

    def parse(self, source_path: Path) -> ParsedDocument:
        if not source_path.is_file():
            raise ResourceNotFoundError(f"PDF file not found: {source_path.name}")

        try:
            with PdfReader(source_path, strict=False) as reader:
                metadata = reader.metadata
                pages = tuple(
                    ParsedPage(page_number=index, text=page.extract_text() or "")
                    for index, page in enumerate(reader.pages, start=1)
                )
                title = _normalize_metadata_value(metadata.title if metadata else None)
                author = _normalize_metadata_value(
                    metadata.author if metadata else None
                )
        except Exception as exc:
            # Malformed PDFs can raise errors outside pypdf's own exception types.
            raise DocumentParseError(
                f"Could not parse PDF: {source_path.name}"
            ) from exc

        return ParsedDocument(
            source_path=source_path,
            title=title,
            author=author,
            pages=pages,
        )
