"""Tests for page-preserving text cleanup."""

from pathlib import Path

import pytest

from neuralnotes.cleaning import (
    clean_document,
    clean_page_text,
    find_repeated_margin_lines,
)
from neuralnotes.parsers.models import ParsedDocument, ParsedPage


def test_clean_page_text_normalizes_spacing_and_line_endings() -> None:
    source = "  Title \t \r\n\n\n First\tparagraph.  \rSecond line. \n\n"

    assert clean_page_text(source) == "Title\n\nFirst paragraph.\nSecond line."


def test_clean_page_text_handles_empty_or_whitespace_input() -> None:
    assert clean_page_text("") == ""
    assert clean_page_text(" \t\r\n\n") == ""


def test_clean_document_preserves_pages_metadata_and_hyphenation() -> None:
    document = ParsedDocument(
        source_path=Path("paper.pdf"),
        title="Example paper",
        author="Researcher",
        pages=(
            ParsedPage(page_number=1, text="retriev-\r\nal\t evidence  \n\n"),
            ParsedPage(page_number=2, text="Second page."),
        ),
    )

    cleaned = clean_document(document)

    assert cleaned is not document
    assert cleaned.source_path == document.source_path
    assert cleaned.title == document.title
    assert cleaned.author == document.author
    assert cleaned.page_count == 2
    assert cleaned.pages == (
        ParsedPage(page_number=1, text="retriev-\nal evidence"),
        ParsedPage(page_number=2, text="Second page."),
    )
    assert document.pages[0].text == "retriev-\r\nal\t evidence  \n\n"


def test_find_repeated_margin_lines_groups_varying_page_numbers() -> None:
    document = ParsedDocument(
        source_path=Path("paper.pdf"),
        title=None,
        author=None,
        pages=(
            ParsedPage(1, "Proceedings 2026\nBody one\nPage 1"),
            ParsedPage(2, "Proceedings 2026\nBody two\nPage 2"),
            ParsedPage(3, "Proceedings 2026\nBody three\nPage 3"),
        ),
    )

    candidates = find_repeated_margin_lines(document, margin_line_count=1)
    actual = [(item.location, item.text, item.page_numbers) for item in candidates]
    expected = [
        ("bottom", "Page 1", (1, 2, 3)),
        ("top", "Proceedings 2026", (1, 2, 3)),
    ]

    assert actual == expected


def test_find_repeated_margin_lines_ignores_numeric_only_lines() -> None:
    document = ParsedDocument(
        source_path=Path("paper.pdf"),
        title=None,
        author=None,
        pages=(
            ParsedPage(1, "Body one\n47578"),
            ParsedPage(2, "Body two\n47579"),
            ParsedPage(3, "Body three\n47580"),
        ),
    )

    assert find_repeated_margin_lines(document, margin_line_count=1) == ()


def test_find_repeated_margin_lines_validates_options() -> None:
    document = ParsedDocument(
        source_path=Path("paper.pdf"),
        title=None,
        author=None,
        pages=(ParsedPage(1, "One"),),
    )

    with pytest.raises(ValueError, match="margin_line_count"):
        find_repeated_margin_lines(document, margin_line_count=0)
    with pytest.raises(ValueError, match="minimum_pages"):
        find_repeated_margin_lines(document, minimum_pages=1)
