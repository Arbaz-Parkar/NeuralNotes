"""Tests for the pypdf-backed PDF parser adapter."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf.errors import PdfReadError

from neuralnotes.errors import DocumentParseError, ResourceNotFoundError
from neuralnotes.parsers import ParsedPage, PypdfDocumentParser
from neuralnotes.parsers import pdf as pdf_parser


class FakePage:
    def __init__(self, text: str | None) -> None:
        self.text = text

    def extract_text(self) -> str | None:
        return self.text


class FakeReader:
    def __init__(self, source_path: Path, strict: bool = True) -> None:
        self.source_path = source_path
        self.strict = strict
        self.metadata = SimpleNamespace(
            title="  Example paper  ", author=" Researcher "
        )
        self.pages = [FakePage(" First page text.\n"), FakePage(None)]
        self.was_closed = False

    def __enter__(self) -> FakeReader:
        return self

    def __exit__(self, *args: object) -> None:
        self.was_closed = True


def test_pdf_parser_preserves_page_text_and_normalizes_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "paper.pdf"
    source_path.write_bytes(b"%PDF-test")
    reader = FakeReader(source_path, strict=False)

    def return_reader(path: Path, strict: bool) -> FakeReader:
        assert path == source_path
        assert strict is False
        return reader

    monkeypatch.setattr(pdf_parser, "PdfReader", return_reader)

    parsed = PypdfDocumentParser().parse(source_path)

    assert parsed.source_path == source_path
    assert parsed.title == "Example paper"
    assert parsed.author == "Researcher"
    assert parsed.page_count == 2
    assert parsed.pages == (
        ParsedPage(page_number=1, text=" First page text.\n"),
        ParsedPage(page_number=2, text=""),
    )
    assert reader.source_path == source_path
    assert reader.strict is False
    assert reader.was_closed


def test_pdf_parser_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ResourceNotFoundError, match="PDF file not found"):
        PypdfDocumentParser().parse(tmp_path / "missing.pdf")


def test_pdf_parser_wraps_pypdf_read_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "broken.pdf"
    source_path.write_bytes(b"not a PDF")

    def fail_to_open(path: Path, strict: bool) -> FakeReader:
        raise PdfReadError("invalid PDF structure")

    monkeypatch.setattr(pdf_parser, "PdfReader", fail_to_open)

    with pytest.raises(DocumentParseError, match="Could not parse PDF") as error:
        PypdfDocumentParser().parse(source_path)

    assert isinstance(error.value.__cause__, PdfReadError)


def test_parsed_page_requires_one_based_page_numbers() -> None:
    with pytest.raises(ValueError, match="start at 1"):
        ParsedPage(page_number=0, text="Page text")
