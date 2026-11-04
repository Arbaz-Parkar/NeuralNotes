"""Tests for fixed-size overlapping chunk generation."""

import re
from collections.abc import Sequence
from pathlib import Path

import pytest

from neuralnotes.chunking import FixedSizeChunker, TokenSpan
from neuralnotes.parsers.models import ParsedDocument, ParsedPage


class WhitespaceTokenizer:
    def token_spans(self, text: str) -> Sequence[TokenSpan]:
        return tuple(
            TokenSpan(match.start(), match.end()) for match in re.finditer(r"\S+", text)
        )


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


def test_fixed_size_chunker_applies_overlap_and_preserves_page_boundaries() -> None:
    document = _document("one two three four five", "six seven")
    chunker = FixedSizeChunker(WhitespaceTokenizer(), chunk_size=3, overlap=1)

    chunks = chunker.chunk(document, document_id="doc-1")

    assert [chunk.text for chunk in chunks] == [
        "one two three ",
        "three four five",
        "six seven",
    ]
    assert [chunk.token_count for chunk in chunks] == [3, 3, 2]
    assert [chunk.page_number for chunk in chunks] == [1, 1, 2]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]
    assert all(chunk.strategy == "fixed_size" for chunk in chunks)
    assert all(chunk.chunk_id for chunk in chunks)


def test_fixed_size_chunker_without_overlap_covers_page_text() -> None:
    document = _document("one two three four five")
    chunker = FixedSizeChunker(WhitespaceTokenizer(), chunk_size=2, overlap=0)

    chunks = chunker.chunk(document, document_id="doc-1")

    assert "".join(chunk.text for chunk in chunks) == document.pages[0].text
    assert [chunk.token_count for chunk in chunks] == [2, 2, 1]


def test_fixed_size_chunker_uses_initial_default_window_and_overlap() -> None:
    text = " ".join(f"token{index}" for index in range(121))
    chunks = FixedSizeChunker(WhitespaceTokenizer()).chunk(
        _document(text), document_id="doc-1"
    )

    assert [chunk.token_count for chunk in chunks] == [100, 41]
    assert chunks[0].text.split()[-20:] == chunks[1].text.split()[:20]


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (3, -1), (3, 3)],
)
def test_fixed_size_chunker_validates_window_options(
    chunk_size: int,
    overlap: int,
) -> None:
    with pytest.raises(ValueError):
        FixedSizeChunker(WhitespaceTokenizer(), chunk_size=chunk_size, overlap=overlap)


def test_fixed_size_chunker_rejects_empty_document_id() -> None:
    chunker = FixedSizeChunker(WhitespaceTokenizer(), chunk_size=2, overlap=0)

    with pytest.raises(ValueError, match="document_id"):
        chunker.chunk(_document("one two"), document_id=" ")


def test_fixed_size_chunker_rejects_overlapping_token_offsets() -> None:
    class OverlappingTokenizer:
        def token_spans(self, text: str) -> Sequence[TokenSpan]:
            return (TokenSpan(0, 3), TokenSpan(2, 5))

    chunker = FixedSizeChunker(OverlappingTokenizer(), chunk_size=2, overlap=0)

    with pytest.raises(ValueError, match="ordered, non-overlapping"):
        chunker.chunk(_document("abcde"), document_id="doc-1")
