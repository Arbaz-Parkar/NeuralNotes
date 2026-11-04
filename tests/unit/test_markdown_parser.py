"""Tests for the Markdown parser adapter."""

from pathlib import Path

from neuralnotes.parsers import MarkdownDocumentParser, ParsedPage


def test_markdown_parser_extracts_first_h1_and_preserves_source(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "notes.md"
    source_text = "## Section\n\n# Project Notes ##\n\nText.\n"
    source_path.write_bytes(source_text.encode("utf-8"))

    parsed = MarkdownDocumentParser().parse(source_path)

    assert parsed.source_path == source_path
    assert parsed.title == "Project Notes"
    assert parsed.author is None
    assert parsed.page_count == 1
    assert parsed.pages == (ParsedPage(page_number=1, text=source_text),)


def test_markdown_parser_ignores_h1_inside_fenced_code(tmp_path: Path) -> None:
    source_path = tmp_path / "example.md"
    source_text = "```markdown\n# Code sample\n```\n\n# Actual title\n"
    source_path.write_bytes(source_text.encode("utf-8"))

    parsed = MarkdownDocumentParser().parse(source_path)

    assert parsed.title == "Actual title"
    assert parsed.pages[0].text == source_text


def test_markdown_parser_returns_no_title_without_h1(tmp_path: Path) -> None:
    source_path = tmp_path / "sections.md"
    source_text = "## Section\n\n### Subsection\n"
    source_path.write_bytes(source_text.encode("utf-8"))

    parsed = MarkdownDocumentParser().parse(source_path)

    assert parsed.title is None
    assert parsed.pages[0].text == source_text
