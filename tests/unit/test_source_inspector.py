"""Tests for line offsets used while manually labeling evaluation evidence."""

from neuralnotes.evaluation.inspect_source import render_page_with_offsets
from neuralnotes.parsers.models import ParsedPage


def test_page_inspector_reports_cleaned_line_offsets() -> None:
    page = ParsedPage(page_number=3, text="First line\nCafé evidence.\n")

    rendered = render_page_with_offsets(page)

    assert "PDF page 3 — cleaned text length 26 characters" in rendered
    assert "[0:10] First line" in rendered
    assert "[11:25] Café evidence." in rendered


def test_page_inspector_handles_empty_page() -> None:
    rendered = render_page_with_offsets(ParsedPage(page_number=1, text=""))

    assert "[0:0] <empty page>" in rendered
