"""Tests for deterministic pseudo-relevance query expansion."""

import pytest

from neuralnotes.chunking import Chunk
from neuralnotes.retrieval import BM25Hit, expand_query_from_hits


def _hit(chunk_id: str, text: str, score: float) -> BM25Hit:
    return BM25Hit(
        chunk=Chunk(
            chunk_id=chunk_id,
            document_id="paper-1",
            text=text,
            page_number=1,
            chunk_index=0,
            start_char=0,
            end_char=len(text),
            token_count=len(text.split()),
            strategy="fixed_size",
        ),
        score=score,
    )


def test_expansion_uses_rank_weighted_terms_and_excludes_query_terms() -> None:
    expanded = expand_query_from_hits(
        "query",
        (
            _hit("first", "query alpha alpha bridge shared the", 2.0),
            _hit("second", "query bridge delta shared", 1.0),
        ),
        term_count=3,
    )

    assert expanded == "query alpha bridge shared"


def test_expansion_returns_original_query_when_no_feedback_terms_exist() -> None:
    assert expand_query_from_hits("query", (), term_count=3) == "query"


@pytest.mark.parametrize(
    ("query", "term_count", "message"),
    [
        (" ", 1, "query"),
        ("query", 0, "term_count"),
        ("query", True, "term_count"),
    ],
)
def test_expansion_rejects_invalid_inputs(
    query: str, term_count: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        expand_query_from_hits(query, (), term_count=term_count)
