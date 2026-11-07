"""Tests for the in-memory BM25 index."""

from math import log

import pytest

from neuralnotes.chunking import Chunk
from neuralnotes.retrieval import BM25Index


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id=f"document-{chunk_id}",
        text=text,
        page_number=1,
        chunk_index=0,
        start_char=0,
        end_char=len(text),
        token_count=max(len(text.split()), 1),
        strategy="fixed_size",
    )


def test_bm25_scores_follow_term_frequency_and_document_length_formula() -> None:
    index = BM25Index(
        (
            _chunk("long", "alpha alpha beta"),
            _chunk("short", "alpha gamma"),
        )
    )

    hits = index.search("alpha", top_k=2)

    idf = log(1 + 0.5 / 2.5)
    expected_long = idf * (2 * 2.5) / (2 + 1.5 * (0.25 + 0.75 * 3 / 2.5))
    expected_short = idf * 2.5 / (1 + 1.5 * (0.25 + 0.75 * 2 / 2.5))
    assert [hit.chunk.chunk_id for hit in hits] == ["long", "short"]
    assert [hit.score for hit in hits] == pytest.approx([expected_long, expected_short])


def test_search_is_case_insensitive_and_ignores_punctuation() -> None:
    index = BM25Index(
        (
            _chunk("first", "A neural retrieval paper."),
            _chunk("second", "Other work."),
        )
    )

    hits = index.search("NEURAL!!!")

    assert [hit.chunk.chunk_id for hit in hits] == ["first"]


def test_search_limits_results_and_keeps_input_order_for_ties() -> None:
    index = BM25Index(
        (
            _chunk("first", "same exact text"),
            _chunk("second", "same exact text"),
            _chunk("third", "same exact text"),
        )
    )

    hits = index.search("same", top_k=2)

    assert [hit.chunk.chunk_id for hit in hits] == ["first", "second"]


@pytest.mark.parametrize("query", ["", "   ", "!!!"])
def test_search_returns_no_hits_when_query_has_no_word_tokens(query: str) -> None:
    index = BM25Index((_chunk("first", "A source passage."),))

    assert index.search(query) == ()


def test_index_accepts_an_iterable_and_reports_document_count() -> None:
    chunks = (_chunk(str(index), f"passage {index}") for index in range(3))

    index = BM25Index(chunks)

    assert index.document_count == 3
    assert len(index.search("passage", top_k=10)) == 3


@pytest.mark.parametrize(
    ("option", "value", "message"),
    [
        ("k1", 0.0, "k1"),
        ("k1", float("inf"), "k1"),
        ("b", -0.1, "b"),
        ("b", 1.1, "b"),
    ],
)
def test_index_rejects_invalid_parameters(
    option: str,
    value: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        BM25Index((_chunk("first", "A source passage."),), **{option: value})


def test_index_rejects_duplicate_chunk_ids() -> None:
    chunk = _chunk("duplicate", "A source passage.")

    with pytest.raises(ValueError, match="Duplicate chunk id"):
        BM25Index((chunk, chunk))


def test_search_rejects_non_positive_top_k() -> None:
    index = BM25Index((_chunk("first", "A source passage."),))

    with pytest.raises(ValueError, match="top_k"):
        index.search("source", top_k=0)


def test_empty_index_returns_no_results() -> None:
    assert BM25Index(()).search("anything") == ()
