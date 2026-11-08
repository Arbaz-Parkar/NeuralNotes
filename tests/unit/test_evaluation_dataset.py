"""Tests for verified retrieval evaluation records."""

import json

import pytest
from pydantic import ValidationError

from neuralnotes.evaluation import EvaluationCase, load_cases


def _record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "query_id": "q1",
        "question": "Where is the evidence?",
        "split": "dev",
        "category": "single_passage",
        "answerable": True,
        "evidence": [
            {
                "document_id": "paper-1",
                "page_number": 1,
                "start_char": 10,
                "end_char": 20,
            }
        ],
        "reference_answer": "The evidence is there.",
        "verified": True,
    }
    record.update(overrides)
    return record


def test_case_requires_evidence_when_answerable() -> None:
    with pytest.raises(ValidationError, match="need evidence"):
        EvaluationCase.model_validate(_record(evidence=[]))


def test_case_requires_unanswerable_category_to_match_flag() -> None:
    with pytest.raises(ValidationError, match="category"):
        EvaluationCase.model_validate(_record(category="unanswerable"))


def test_case_rejects_zero_length_evidence_span() -> None:
    with pytest.raises(ValidationError, match="positive character length"):
        EvaluationCase.model_validate(
            _record(
                evidence=[
                    {
                        "document_id": "paper-1",
                        "page_number": 1,
                        "start_char": 4,
                        "end_char": 4,
                    }
                ]
            )
        )


def test_loader_filters_unverified_cases_and_split(tmp_path) -> None:
    records = [
        _record(),
        _record(query_id="draft", verified=False),
        _record(query_id="test-case", split="test"),
    ]
    path = tmp_path / "cases.jsonl"
    path.write_text(
        "\n".join(json.dumps(record) for record in records), encoding="utf-8"
    )

    assert [case.query_id for case in load_cases(path, split="dev")] == ["q1"]
    assert [case.query_id for case in load_cases(path, split="test")] == ["test-case"]


def test_loader_rejects_duplicate_ids_and_empty_verified_split(tmp_path) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text(
        json.dumps(_record()) + "\n" + json.dumps(_record()), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Duplicate"):
        load_cases(path, split="dev")

    path.write_text(json.dumps(_record(split="test")), encoding="utf-8")
    with pytest.raises(ValueError, match="No verified"):
        load_cases(path, split="dev")
