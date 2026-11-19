"""Summarize human-labeled answer grounding audits."""

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

GroundingLabel = Literal[
    "supported", "partially_supported", "unsupported", "unverifiable"
]
_LABELS: tuple[GroundingLabel, ...] = (
    "supported",
    "partially_supported",
    "unsupported",
    "unverifiable",
)
_ANSWER_LABELS = (
    "fully_supported",
    "partially_supported",
    "unsupported",
    "unverifiable",
)


class CitationEvidence(BaseModel):
    """A cited passage copied into an audit record for reproducible review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    text: str = Field(min_length=1)


class GroundingAuditRecord(BaseModel):
    """One human judgment for one answer claim and its cited passages."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    citations: tuple[CitationEvidence, ...] = Field(min_length=1)
    label: GroundingLabel
    reviewer: str = Field(min_length=1)
    note: str = ""


def load_audit_records(path: Path) -> tuple[GroundingAuditRecord, ...]:
    """Load validated claim judgments from a JSONL audit file."""
    records: list[GroundingAuditRecord] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"Could not read audit file: {path}") from exc

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            records.append(GroundingAuditRecord.model_validate_json(line))
        except ValidationError as exc:
            raise ValueError(
                f"Invalid audit record on line {line_number}: {exc}"
            ) from exc

    if not records:
        raise ValueError(f"Audit file contains no records: {path}")
    return tuple(records)


def summarize_audit(
    records: tuple[GroundingAuditRecord, ...], *, source: str
) -> dict[str, object]:
    """Return counts and rates for claim judgments and reviewer/query answers."""
    if not records:
        raise ValueError("At least one grounding audit record is required.")

    claim_counts = Counter(record.label for record in records)
    rated_claim_count = len(records) - claim_counts["unverifiable"]
    answer_labels: dict[tuple[str, str], list[GroundingLabel]] = defaultdict(list)
    for record in records:
        answer_labels[(record.reviewer, record.query_id)].append(record.label)

    answer_counts: Counter[str] = Counter()
    for labels in answer_labels.values():
        if all(label == "supported" for label in labels):
            answer_counts["fully_supported"] += 1
        elif "unsupported" in labels:
            answer_counts["unsupported"] += 1
        elif "partially_supported" in labels:
            answer_counts["partially_supported"] += 1
        else:
            answer_counts["unverifiable"] += 1

    rated_answer_count = sum(
        answer_counts[label]
        for label in ("fully_supported", "partially_supported", "unsupported")
    )
    return {
        "audit_schema_version": 1,
        "source": source,
        "claim_judgment_count": len(records),
        "query_count": len({record.query_id for record in records}),
        "reviewer_count": len({record.reviewer for record in records}),
        "claim_label_counts": {label: claim_counts[label] for label in _LABELS},
        "rated_claim_count": rated_claim_count,
        "claim_support_rate": (
            claim_counts["supported"] / rated_claim_count if rated_claim_count else None
        ),
        "answer_count": len(answer_labels),
        "answer_label_counts": {
            label: answer_counts[label] for label in _ANSWER_LABELS
        },
        "rated_answer_count": rated_answer_count,
        "fully_supported_answer_rate": (
            answer_counts["fully_supported"] / rated_answer_count
            if rated_answer_count
            else None
        ),
    }


def _render_markdown(summary: dict[str, object]) -> str:
    claim_counts = summary["claim_label_counts"]
    answer_counts = summary["answer_label_counts"]
    assert isinstance(claim_counts, dict)
    assert isinstance(answer_counts, dict)
    claim_rate = summary["claim_support_rate"]
    answer_rate = summary["fully_supported_answer_rate"]
    claim_rate_text = "n/a" if claim_rate is None else f"{claim_rate:.3f}"
    answer_rate_text = "n/a" if answer_rate is None else f"{answer_rate:.3f}"
    lines = [
        "# Answer grounding audit summary",
        "",
        f"- Source: `{summary['source']}`",
        f"- Claim judgments: {summary['claim_judgment_count']}",
        f"- Queries: {summary['query_count']}",
        f"- Reviewers: {summary['reviewer_count']}",
        "",
        "## Claim judgments",
        "",
        "| Label | Count |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {label} | {claim_counts[label]} |" for label in _LABELS)
    lines.extend(
        [
            "",
            f"Supported claim rate: **{claim_rate_text}** "
            f"({claim_counts['supported']} / "
            f"{summary['rated_claim_count']} rated claims).",
            "",
            "## Answer judgments",
            "",
            "| Label | Count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(f"| {label} | {answer_counts[label]} |" for label in _ANSWER_LABELS)
    lines.extend(
        [
            "",
            f"Fully supported answer rate: **{answer_rate_text}** "
            f"({answer_counts['fully_supported']} / "
            f"{summary['rated_answer_count']} rated answers).",
            "",
            "Unverifiable judgments are excluded from support-rate denominators.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Load a JSONL audit and write timestamped JSON and Markdown summaries."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/processed/evaluations/grounding")
    )
    args = parser.parse_args(argv)
    try:
        records = load_audit_records(args.input)
        summary = summarize_audit(records, source=args.input.name)
    except ValueError as exc:
        parser.error(str(exc))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    stem = f"{args.input.stem}__grounding__{timestamp}"
    json_path = args.output_dir / f"{stem}.json"
    markdown_path = args.output_dir / f"{stem}.md"
    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(_render_markdown(summary), encoding="utf-8")
    print(f"Wrote grounding JSON to {json_path}")
    print(f"Wrote grounding Markdown to {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
