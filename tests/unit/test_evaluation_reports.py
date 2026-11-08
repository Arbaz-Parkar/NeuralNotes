"""Tests for versioned retrieval evaluation report files."""

import json
from uuid import uuid4

import pytest

from neuralnotes.chunking import Chunk
from neuralnotes.evaluation import EvaluationCase, evaluate_retrieval
from neuralnotes.evaluation.reports import write_evaluation_reports


def test_report_writer_saves_json_and_markdown_with_run_configuration(tmp_path) -> None:
    workspace_id = uuid4()
    chunk = Chunk(
        chunk_id="relevant",
        document_id="paper-1",
        text="A source passage.",
        page_number=1,
        chunk_index=0,
        start_char=0,
        end_char=17,
        token_count=3,
        strategy="fixed_size",
    )
    case = EvaluationCase(
        query_id="q1",
        question="What is in the source?",
        split="dev",
        category="single_passage",
        answerable=True,
        evidence=(
            {
                "document_id": "paper-1",
                "page_number": 1,
                "start_char": 0,
                "end_char": 17,
            },
        ),
        verified=True,
    )
    report = evaluate_retrieval(
        (case,), (chunk,), lambda *_: ("relevant",), k_values=(1,)
    )

    json_path, markdown_path = write_evaluation_reports(
        report,
        tmp_path,
        dataset_version="dev-v1",
        workspace_id=workspace_id,
        run_id="run-001",
        evidence_overlap=0.5,
        bm25_k1=1.5,
        bm25_b=0.75,
        chunk_count=1,
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert payload["workspace_id"] == str(workspace_id)
    assert payload["report_schema_version"] == 2
    assert payload["dataset_version"] == "dev-v1"
    assert payload["retriever"] == {"b": 0.75, "k1": 1.5, "name": "BM25"}
    assert payload["metrics_at_k"]["1"]["recall"] == 1.0
    assert payload["confidence_intervals_at_k"]["1"]["recall"]["lower"] == 1.0
    assert payload["bootstrap"]["seed"] == 0
    assert "one query" in markdown
    assert json_path.name.endswith("run-001.json")


@pytest.mark.parametrize("unsafe", ["../escape", "white space", "", "."])
def test_report_writer_rejects_unsafe_version_names(tmp_path, unsafe: str) -> None:
    from neuralnotes.evaluation.runner import EvaluationReport

    report = EvaluationReport("dev", 1, 0, (1,), {"1": {}}, ())
    with pytest.raises(ValueError, match="dataset_version"):
        write_evaluation_reports(
            report,
            tmp_path,
            dataset_version=unsafe,
            workspace_id=uuid4(),
            run_id="run-001",
            evidence_overlap=0.5,
            bm25_k1=1.5,
            bm25_b=0.75,
            chunk_count=0,
        )
