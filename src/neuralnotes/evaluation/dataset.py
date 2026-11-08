"""Validated JSONL records for source-span retrieval evaluation."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EvidenceSpan(BaseModel):
    """End-exclusive character evidence in one source document."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_span(self) -> "EvidenceSpan":
        if self.end_char <= self.start_char:
            raise ValueError("Evidence spans must have a positive character length.")
        return self


class EvaluationCase(BaseModel):
    """One verified or draft question with source evidence labels."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    split: Literal["dev", "test"]
    category: Literal[
        "single_passage",
        "multi_hop",
        "comparison",
        "numeric",
        "unanswerable",
    ]
    answerable: bool
    evidence: tuple[EvidenceSpan, ...] = ()
    reference_answer: str | None = None
    verified: bool = False

    @field_validator("query_id", "question")
    @classmethod
    def require_non_whitespace(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field must contain non-whitespace text.")
        return cleaned

    @model_validator(mode="after")
    def validate_evidence_labels(self) -> "EvaluationCase":
        if self.answerable != bool(self.evidence):
            raise ValueError(
                "Answerable cases need evidence; unanswerable cases must not have it."
            )
        if (self.category == "unanswerable") == self.answerable:
            raise ValueError(
                "The unanswerable category must match the answerable flag."
            )
        return self


def load_cases(path: Path, *, split: str) -> tuple[EvaluationCase, ...]:
    """Load verified cases from JSONL, selecting one split and rejecting bad labels."""
    if split not in {"dev", "test"}:
        raise ValueError("split must be 'dev' or 'test'.")

    cases: list[EvaluationCase] = []
    seen_ids: set[str] = set()
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                case = EvaluationCase.model_validate_json(line)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid evaluation record on line {line_number}: {exc}"
                ) from exc
            if case.query_id in seen_ids:
                raise ValueError(f"Duplicate evaluation query_id: {case.query_id}.")
            seen_ids.add(case.query_id)
            if case.split == split and case.verified:
                cases.append(case)

    if not cases:
        raise ValueError(f"No verified evaluation cases found for split '{split}'.")
    return tuple(cases)
