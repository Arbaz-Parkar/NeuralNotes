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
    answerable_cases = tuple(case for case in cases if case.answerable)
    unanswerable_cases = tuple(case for case in cases if not case.answerable)

    assert len(cases) == 62
    assert len(answerable_cases) == 56
    assert len(unanswerable_cases) == 6
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
        "r2ag-dev-001",
        "r2ag-dev-002",
        "r2ag-dev-003",
        "r2ag-dev-004",
        "r2ag-dev-005",
        "r2ag-dev-006",
        "r2ag-dev-007",
        "bergen-dev-001",
        "bergen-dev-002",
        "bergen-dev-003",
        "bergen-dev-004",
        "bergen-dev-005",
        "ragas-dev-001",
        "ragas-dev-002",
        "ragas-dev-003",
        "ragas-dev-004",
        "ragas-dev-005",
        "ragas-dev-006",
        "dxr-dev-007",
        "dxr-dev-008",
        "dxr-dev-009",
        "dxr-dev-010",
        "dxr-dev-011",
        "dxr-dev-012",
        "ragbp-dev-001",
        "ragbp-dev-002",
        "ragbp-dev-003",
        "ragbp-dev-004",
        "ragbp-dev-005",
        "ragbp-dev-006",
        "mirage-dev-001",
        "mirage-dev-002",
        "mirage-dev-003",
        "mirage-dev-004",
        "flare-dev-001",
        "flare-dev-002",
        "flare-dev-003",
        "flare-dev-004",
        "flare-dev-005",
        "rarag-dev-001",
        "rarag-dev-002",
        "rarag-dev-003",
        "rarag-dev-004",
        "rarag-dev-005",
        "rarag-dev-006",
        "unans-dev-001",
        "unans-dev-002",
        "unans-dev-003",
        "unans-dev-004",
        "unans-dev-005",
        "unans-dev-006",
    }
    assert all(case.verified for case in cases)
    assert {case.query_id for case in unanswerable_cases} == {
        "unans-dev-001",
        "unans-dev-002",
        "unans-dev-003",
        "unans-dev-004",
        "unans-dev-005",
        "unans-dev-006",
    }
    assert {
        case.query_id: tuple(
            (span.document_id, span.page_number, span.start_char, span.end_char)
            for span in case.evidence
        )
        for case in answerable_cases
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
        "r2ag-dev-001": (("2024.findings-emnlp.678", 1, 744, 860),),
        "r2ag-dev-002": (("2024.findings-emnlp.678", 1, 875, 1144),),
        "r2ag-dev-003": (("2024.findings-emnlp.678", 1, 1145, 1282),),
        "r2ag-dev-004": (("2024.findings-emnlp.678", 1, 1283, 1514),),
        "r2ag-dev-005": (("2024.findings-emnlp.678", 1, 1515, 1605),),
        "r2ag-dev-006": (("2024.findings-emnlp.678", 1, 1606, 1703),),
        "r2ag-dev-007": (("2024.findings-emnlp.678", 1, 1704, 1846),),
        "bergen-dev-001": (("2024.findings-emnlp.449", 1, 775, 869),),
        "bergen-dev-002": (("2024.findings-emnlp.449", 1, 870, 1003),),
        "bergen-dev-003": (("2024.findings-emnlp.449", 1, 1004, 1229),),
        "bergen-dev-004": (("2024.findings-emnlp.449", 1, 1230, 1370),),
        "bergen-dev-005": (("2024.findings-emnlp.449", 1, 2787, 2942),),
        "ragas-dev-001": (("2024.eacl-demo.16", 1, 531, 700),),
        "ragas-dev-002": (("2024.eacl-demo.16", 1, 1013, 1251),),
        "ragas-dev-003": (("2024.eacl-demo.16", 1, 1252, 1427),),
        "ragas-dev-004": (("2024.eacl-demo.16", 1, 3416, 3615),),
        "ragas-dev-005": (("2024.eacl-demo.16", 1, 3818, 4061),),
        "ragas-dev-006": (("2024.eacl-demo.16", 1, 4062, 4251),),
        "dxr-dev-007": (("2024.emnlp-main.845", 2, 1691, 1990),),
        "dxr-dev-008": (("2024.emnlp-main.845", 2, 1991, 2447),),
        "dxr-dev-009": (("2024.emnlp-main.845", 2, 3098, 3321),),
        "dxr-dev-010": (("2024.emnlp-main.845", 2, 3322, 3566),),
        "dxr-dev-011": (("2024.emnlp-main.845", 2, 3916, 4069),),
        "dxr-dev-012": (("2024.emnlp-main.845", 2, 4413, 4542),),
        "ragbp-dev-001": (("2024.emnlp-main.981", 1, 617, 846),),
        "ragbp-dev-002": (("2024.emnlp-main.981", 1, 847, 1167),),
        "ragbp-dev-003": (("2024.emnlp-main.981", 1, 1168, 1444),),
        "ragbp-dev-004": (("2024.emnlp-main.981", 1, 1445, 1724),),
        "ragbp-dev-005": (("2024.emnlp-main.981", 1, 2688, 3249),),
        "ragbp-dev-006": (("2024.emnlp-main.981", 1, 3250, 3551),),
        "mirage-dev-001": (("2025.findings-naacl.157", 1, 892, 1167),),
        "mirage-dev-002": (("2025.findings-naacl.157", 1, 1168, 1389),),
        "mirage-dev-003": (("2025.findings-naacl.157", 1, 615, 892),),
        "mirage-dev-004": (
            ("2025.findings-naacl.157", 1, 3131, 3596),
            ("2025.findings-naacl.157", 1, 3597, 4013),
        ),
        "flare-dev-001": (("2023.emnlp-main.495", 1, 799, 1074),),
        "flare-dev-002": (("2023.emnlp-main.495", 1, 1075, 1262),),
        "flare-dev-003": (("2023.emnlp-main.495", 1, 1263, 1585),),
        "flare-dev-004": (("2023.emnlp-main.495", 1, 1585, 1718),),
        "flare-dev-005": (("2023.emnlp-main.495", 1, 1585, 1798),),
        "rarag-dev-001": (("2025.emnlp-main.1738", 1, 717, 906),),
        "rarag-dev-002": (("2025.emnlp-main.1738", 1, 1219, 1540),),
        "rarag-dev-003": (("2025.emnlp-main.1738", 1, 1408, 1540),),
        "rarag-dev-004": (("2025.emnlp-main.1738", 1, 1541, 1724),),
        "rarag-dev-005": (("2025.emnlp-main.1738", 1, 1725, 1868),),
        "rarag-dev-006": (
            ("2025.emnlp-main.1738", 1, 2702, 2815),
            ("2025.emnlp-main.1738", 1, 3194, 3283),
        ),
    }


def test_committed_test_cases_are_verified_and_point_to_source_pages() -> None:
    dataset_path = Path(__file__).parents[2] / "data" / "evaluation" / "golden.jsonl"

    cases = load_cases(dataset_path, split="test")

    expected_spans = {
        "ragbp-test-001": (("2024.emnlp-main.981", 2, 209, 308),),
        "ragbp-test-002": (("2024.emnlp-main.981", 2, 406, 551),),
        "ragbp-test-003": (("2024.emnlp-main.981", 2, 4278, 4314),),
        "mirage-test-001": (("2025.findings-naacl.157", 2, 4015, 4158),),
        "mirage-test-002": (("2025.findings-naacl.157", 2, 4476, 4775),),
        "mirage-test-003": (("2025.findings-naacl.157", 2, 4789, 4879),),
        "flare-test-001": (("2023.emnlp-main.495", 2, 2445, 2546),),
        "flare-test-002": (("2023.emnlp-main.495", 2, 2853, 3007),),
        "flare-test-003": (("2023.emnlp-main.495", 2, 3060, 3270),),
        "rarag-test-001": (("2025.emnlp-main.1738", 2, 98, 256),),
        "rarag-test-002": (("2025.emnlp-main.1738", 2, 1819, 1915),),
        "rarag-test-003": (("2025.emnlp-main.1738", 2, 2852, 3048),),
        "ragbp-test-004": (("2024.emnlp-main.981", 2, 2976, 3070),),
        "ragbp-test-005": (("2024.emnlp-main.981", 2, 3118, 3162),),
        "mirage-test-004": (("2025.findings-naacl.157", 2, 4360, 4409),),
        "flare-test-004": (("2023.emnlp-main.495", 2, 1625, 1679),),
        "rarag-test-004": (("2025.emnlp-main.1738", 2, 2111, 2256),),
        "rarag-test-005": (("2025.emnlp-main.1738", 2, 650, 957),),
    }

    answerable_cases = tuple(case for case in cases if case.answerable)
    unanswerable_cases = tuple(case for case in cases if not case.answerable)

    assert len(cases) == 24
    assert len(answerable_cases) == 18
    assert len(unanswerable_cases) == 6
    assert all(case.verified for case in cases)
    assert all(
        case.category == "unanswerable" and not case.evidence
        for case in unanswerable_cases
    )
    assert {case.query_id for case in unanswerable_cases} == {
        "unans-test-007",
        "unans-test-008",
        "unans-test-009",
        "unans-test-010",
        "unans-test-011",
        "unans-test-012",
    }
    assert {
        case.query_id: tuple(
            (span.document_id, span.page_number, span.start_char, span.end_char)
            for span in case.evidence
        )
        for case in answerable_cases
    } == expected_spans
