"""Tests for verified retrieval evaluation records."""

import json
from pathlib import Path

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


def test_committed_pilot_cases_are_verified_and_point_to_source_pages() -> None:
    dataset_path = Path(__file__).parents[2] / "data" / "evaluation" / "golden.jsonl"

    cases = load_cases(dataset_path, split="dev")

    assert len(cases) == 11
    assert cases[0].query_id == "dpr-dev-001"
    assert cases[0].verified is True
    assert cases[0].evidence[0].document_id == "2020.emnlp-main.550"
    assert cases[0].evidence[0].page_number == 1
    assert (cases[0].evidence[0].start_char, cases[0].evidence[0].end_char) == (
        753,
        944,
    )
    assert {case.query_id for case in cases} == {
        "dpr-dev-001",
        "dpr-dev-002",
        "dpr-dev-003",
        "dpr-dev-004",
        "dpr-dev-005",
        "dxr-dev-001",
        "dxr-dev-002",
        "dxr-dev-003",
        "dxr-dev-004",
        "dxr-dev-005",
        "dxr-dev-006",
    }
    assert all(case.verified for case in cases)
    assert {
        case.query_id: tuple(
            (span.document_id, span.page_number, span.start_char, span.end_char)
            for span in case.evidence
        )
        for case in cases
    } == {
        "dpr-dev-001": (("2020.emnlp-main.550", 1, 753, 944),),
        "dpr-dev-002": (("2020.emnlp-main.550", 1, 531, 725),),
        "dpr-dev-003": (("2020.emnlp-main.550", 1, 1008, 1142),),
        "dpr-dev-004": (("2020.emnlp-main.550", 1, 1601, 1872),),
        "dpr-dev-005": (("2020.emnlp-main.550", 1, 2177, 2287),),
        "dxr-dev-001": (("2024.emnlp-main.845", 1, 659, 799),),
        "dxr-dev-002": (("2024.emnlp-main.845", 1, 1036, 1221),),
        "dxr-dev-003": (("2024.emnlp-main.845", 1, 989, 1035),),
        "dxr-dev-004": (("2024.emnlp-main.845", 1, 1315, 1455),),
        "dxr-dev-005": (("2024.emnlp-main.845", 1, 1455, 1619),),
        "dxr-dev-006": (
            ("2024.emnlp-main.845", 1, 3822, 3913),
            ("2024.emnlp-main.845", 1, 3914, 4010),
        ),
    }
