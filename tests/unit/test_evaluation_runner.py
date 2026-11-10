"""Tests for evidence-span mapping and retrieval experiment aggregation."""

import pytest

from neuralnotes.chunking import Chunk
from neuralnotes.evaluation import (
    EvaluationCase,
    evaluate_retrieval,
    relevant_chunk_ids,
)


def _chunk(
    chunk_id: str,
    document_id: str,
    start: int,
    end: int,
    strategy: str = "fixed_size",
    page_number: int = 1,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id=document_id,
        text=f"Passage {chunk_id}",
        page_number=page_number,
        chunk_index=0,
        start_char=start,
        end_char=end,
        token_count=2,
        strategy=strategy,
    )


def _case(
    query_id: str = "q1",
    *,
    split: str = "dev",
    answerable: bool = True,
    verified: bool = True,
    question: str = "What does the passage say?",
) -> EvaluationCase:
    return EvaluationCase(
        query_id=query_id,
        question=question,
        split=split,
        category="single_passage" if answerable else "unanswerable",
        answerable=answerable,
        evidence=(
            (
                {
                    "document_id": "paper-1",
                    "page_number": 1,
                    "start_char": 10,
                    "end_char": 20,
                },
            )
            if answerable
            else ()
        ),
        verified=verified,
    )


def test_span_mapping_uses_document_and_overlap_threshold() -> None:
    case = _case()
    chunks = (
        _chunk("enough", "paper-1", 5, 17),
        _chunk("too-little", "paper-1", 18, 30),
        _chunk("other-document", "paper-2", 10, 20),
    )
    chunks = (*chunks, _chunk("other-page", "paper-1", 10, 20, page_number=2))

    assert relevant_chunk_ids(chunks, case) == {"enough"}


def test_runner_aggregates_answerable_queries_and_reports_excluded_unanswerables() -> (
    None
):
    chunks = (_chunk("relevant", "paper-1", 10, 20), _chunk("noise", "paper-2", 0, 10))
    cases = (_case(), _case("q2", answerable=False, question="unknown query"))
    report = evaluate_retrieval(
        cases,
        chunks,
        lambda query, _top_k: () if query == "unknown query" else ["noise", "relevant"],
        k_values=(1, 2),
    )

    assert report.answerable_query_count == 1
    assert report.excluded_unanswerable_query_count == 1
    assert report.unanswerable_query_count == 1
    assert report.unanswerable_empty_result_count == 1
    assert report.unanswerable_empty_result_rate == 1.0
    assert report.metrics_at_k["2"]["recall"] == 1.0
    assert report.metrics_at_k["2"]["mrr"] == 0.5
    assert report.to_dict()["split"] == "dev"


def test_runner_rejects_evidence_without_matching_chunks() -> None:
    with pytest.raises(ValueError, match="No chunks overlap evidence"):
        evaluate_retrieval(
            (_case(),), (_chunk("wrong", "paper-1", 50, 60),), lambda *_: []
        )


def test_runner_rejects_mixed_splits_and_invalid_k_values() -> None:
    chunks = (_chunk("relevant", "paper-1", 10, 20),)
    with pytest.raises(ValueError, match="exactly one dataset split"):
        evaluate_retrieval((_case(), _case("q2", split="test")), chunks, lambda *_: [])
    with pytest.raises(ValueError, match="positive integers"):
        evaluate_retrieval((_case(),), chunks, lambda *_: [], k_values=(0,))
