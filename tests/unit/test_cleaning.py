"""Tests for page-preserving text cleanup."""

from pathlib import Path

from neuralnotes.cleaning import clean_document, clean_page_text
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
