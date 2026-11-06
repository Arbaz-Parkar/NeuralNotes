"""Tests for sentence-centered chunks with neighboring context."""

import re
from collections.abc import Sequence
from pathlib import Path

import pytest

from neuralnotes.chunking import SentenceWindowChunker, TokenSpan
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


def test_sentence_window_chunker_expands_to_neighbor_sentences() -> None:
    document = _document("Alpha one. Beta two. Gamma three. Delta four.")
    chunker = SentenceWindowChunker(
        WhitespaceTokenizer(), context_sentences=1, max_tokens=100
    )

    chunks = chunker.chunk(document, document_id="doc-1")

    assert [chunk.text.strip() for chunk in chunks] == [
        "Alpha one. Beta two.",
        "Alpha one. Beta two. Gamma three.",
        "Beta two. Gamma three. Delta four.",
        "Gamma three. Delta four.",
    ]
    assert all(chunk.strategy == "sentence_window" for chunk in chunks)


def test_sentence_windows_respect_token_cap_and_deduplicate() -> None:
    document = _document("Alpha one. Beta two. Gamma three.")
    chunker = SentenceWindowChunker(
        WhitespaceTokenizer(), context_sentences=1, max_tokens=4
    )

    chunks = chunker.chunk(document, document_id="doc-1")

    assert all(chunk.token_count <= 4 for chunk in chunks)
    source_ranges = {(chunk.start_char, chunk.end_char) for chunk in chunks}
    assert len(source_ranges) == len(chunks)


def test_sentence_window_chunker_splits_a_sentence_over_the_token_cap() -> None:
    chunker = SentenceWindowChunker(
        WhitespaceTokenizer(), context_sentences=1, max_tokens=3
    )

    chunks = chunker.chunk(
        _document("one two three four five six seven"), document_id="doc-1"
    )

    assert [chunk.text.strip() for chunk in chunks] == [
        "one two three",
        "four five six",
        "seven",
    ]
    assert all(chunk.token_count <= 3 for chunk in chunks)


def test_sentence_window_chunker_avoids_common_abbreviation_boundaries() -> None:
    text = "Prior work (e.g. Smith et al., 2020) reports results. Here it starts."
    chunker = SentenceWindowChunker(
        WhitespaceTokenizer(), context_sentences=0, max_tokens=100
    )

    chunks = chunker.chunk(_document(text), document_id="doc-1")

    assert len(chunks) == 2
    assert chunks[0].text.strip().endswith("results.")
    assert chunks[1].text.strip() == "Here it starts."


def test_sentence_window_chunker_keeps_pages_separate_and_ids_stable() -> None:
    document = _document("One sentence.", "Another sentence.")
    chunker = SentenceWindowChunker(WhitespaceTokenizer())

    first = chunker.chunk(document, document_id="doc-1")
    second = chunker.chunk(document, document_id="doc-1")

    assert [chunk.page_number for chunk in first] == [1, 2]
    first_ids = [chunk.chunk_id for chunk in first]
    second_ids = [chunk.chunk_id for chunk in second]
    assert first_ids == second_ids


@pytest.mark.parametrize(
    ("context_sentences", "max_tokens"),
    [(-1, 10), (0, 0)],
)
def test_sentence_window_chunker_validates_options(
    context_sentences: int,
    max_tokens: int,
) -> None:
    with pytest.raises(ValueError):
        SentenceWindowChunker(
            WhitespaceTokenizer(),
            context_sentences=context_sentences,
            max_tokens=max_tokens,
        )


def test_sentence_window_chunker_rejects_empty_document_id() -> None:
    chunker = SentenceWindowChunker(WhitespaceTokenizer())

    with pytest.raises(ValueError, match="document_id"):
        chunker.chunk(_document("One sentence."), document_id=" ")
