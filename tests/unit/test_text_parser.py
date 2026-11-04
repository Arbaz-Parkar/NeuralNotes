"""Tests for the plain-text parser adapter."""

from pathlib import Path

import pytest

from neuralnotes.errors import DocumentParseError, ResourceNotFoundError
from neuralnotes.parsers import ParsedPage, PlainTextDocumentParser


def test_text_parser_preserves_utf8_text_and_line_endings(tmp_path: Path) -> None:
    source_path = tmp_path / "notes.txt"
    source_text = "First line.\r\nCafé and 日本語.\rFinal line."
    source_path.write_bytes(source_text.encode("utf-8"))

    parsed = PlainTextDocumentParser().parse(source_path)

    assert parsed.source_path == source_path
    assert parsed.title is None
    assert parsed.author is None
    assert parsed.page_count == 1
    assert parsed.pages == (ParsedPage(page_number=1, text=source_text),)


def test_text_parser_strips_optional_utf8_bom(tmp_path: Path) -> None:
    source_path = tmp_path / "notes.txt"
    source_path.write_bytes(b"\xef\xbb\xbfNotes with a BOM.")

    parsed = PlainTextDocumentParser().parse(source_path)

    assert parsed.pages[0].text == "Notes with a BOM."


def test_text_parser_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ResourceNotFoundError, match="Text file not found"):
        PlainTextDocumentParser().parse(tmp_path / "missing.txt")


def test_text_parser_wraps_invalid_utf8(tmp_path: Path) -> None:
    source_path = tmp_path / "invalid.txt"
    source_path.write_bytes(b"\xff")

    with pytest.raises(DocumentParseError, match="not valid UTF-8") as error:
        PlainTextDocumentParser().parse(source_path)

    assert isinstance(error.value.__cause__, UnicodeDecodeError)
