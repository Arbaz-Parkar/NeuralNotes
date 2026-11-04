"""Plain-text document parser adapter."""

from pathlib import Path

from neuralnotes.errors import DocumentParseError, ResourceNotFoundError
from neuralnotes.parsers.models import ParsedDocument, ParsedPage


class PlainTextDocumentParser:
    """Read a UTF-8 text file as one source page without changing its text."""

    def parse(self, source_path: Path) -> ParsedDocument:
        if not source_path.is_file():
            raise ResourceNotFoundError(f"Text file not found: {source_path.name}")

        try:
            text = source_path.read_bytes().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentParseError(
                f"Text file is not valid UTF-8: {source_path.name}"
            ) from exc
        except OSError as exc:
            raise DocumentParseError(
                f"Could not read text file: {source_path.name}"
            ) from exc

        return ParsedDocument(
            source_path=source_path,
            title=None,
            author=None,
            pages=(ParsedPage(page_number=1, text=text),),
        )
