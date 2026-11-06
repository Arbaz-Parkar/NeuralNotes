"""Tests for structure-aware recursive chunk generation."""

import re
from collections.abc import Sequence
from pathlib import Path

import pytest

from neuralnotes.chunking import RecursiveChunker, TokenSpan
from neuralnotes.parsers.models import ParsedDocument, ParsedPage


class WhitespaceTokenizer:
    def token_spans(self, text: str) -> Sequence[TokenSpan]:
        return tuple(
            TokenSpan(match.start(), match.end()) for match in re.finditer(r"\S+", text)
        )


class CharacterTokenizer:
    def token_spans(self, text: str) -> Sequence[TokenSpan]:
        return tuple(TokenSpan(index, index + 1) for index in range(len(text)))


def _document(*pages: str) -> ParsedDocument:
    return ParsedDocument(
        source_path=Path("paper.pdf"),
        title="Example paper",
        author=None,
        pages=tuple(
            ParsedPage(page_number=index, text=text)
            for index, text in enumerate(pages, start=1)
        ),
    )


def test_recursive_chunker_prefers_paragraph_break_and_keeps_overlap() -> None:
    text = "one two three four five\n\nsix seven eight nine ten"
    chunker = RecursiveChunker(WhitespaceTokenizer(), chunk_size=7, overlap=1)

    chunks = chunker.chunk(_document(text), document_id="doc-1")

    assert chunks[0].text == "one two three four five\n\n"
    assert chunks[1].text == "five\n\nsix seven eight nine ten"
    assert [chunk.token_count for chunk in chunks] == [5, 6]
    assert all(chunk.strategy == "recursive" for chunk in chunks)


def test_recursive_chunker_uses_sentence_boundary_when_no_paragraph_fits() -> None:
    text = "Alpha beta. Gamma delta. Epsilon zeta."
    chunker = RecursiveChunker(WhitespaceTokenizer(), chunk_size=5, overlap=0)

    chunks = chunker.chunk(_document(text), document_id="doc-1")

    assert chunks[0].text == "Alpha beta. Gamma delta. "
    assert chunks[0].token_count == 4
    assert chunks[1].text == "Epsilon zeta."


def test_recursive_chunker_falls_back_to_token_limit() -> None:
    chunks = RecursiveChunker(CharacterTokenizer(), chunk_size=3, overlap=0).chunk(
        _document("abcdefghij"), document_id="doc-1"
    )

    assert [chunk.text for chunk in chunks] == ["abc", "def", "ghi", "j"]
    assert all(chunk.token_count <= 3 for chunk in chunks)


def test_recursive_chunker_keeps_pages_separate_and_ids_stable() -> None:
    document = _document("one two", "three four")
    chunker = RecursiveChunker(WhitespaceTokenizer(), chunk_size=3, overlap=1)

    first = chunker.chunk(document, document_id="doc-1")
    second = chunker.chunk(document, document_id="doc-1")

    assert [chunk.page_number for chunk in first] == [1, 2]
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (3, -1), (3, 3)],
)
def test_recursive_chunker_validates_window_options(
    chunk_size: int,
    overlap: int,
) -> None:
    with pytest.raises(ValueError):
        RecursiveChunker(WhitespaceTokenizer(), chunk_size=chunk_size, overlap=overlap)


def test_recursive_chunker_rejects_empty_document_id() -> None:
    chunker = RecursiveChunker(WhitespaceTokenizer(), chunk_size=2, overlap=0)

    with pytest.raises(ValueError, match="document_id"):
        chunker.chunk(_document("one two"), document_id=" ")
