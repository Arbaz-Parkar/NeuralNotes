"""Tests for PDF parser comparison metrics and local review artifacts."""

import csv

from neuralnotes.parser_comparison import (
    MANUAL_REVIEW_FIELDS,
    PARSER_NAMES,
    SAMPLE_PAPER_IDS,
    _write_manual_review_template,
    summarize_pages,
)


def test_summarize_pages_counts_text_and_bad_characters() -> None:
    metrics = summarize_pages(["Title alpha\ufffd\x01", "  ", "x y"])

    assert metrics == {
        "page_count": 3,
        "empty_pages": 1,
        "characters": 18,
        "words": 4,
        "replacement_characters": 1,
        "control_characters": 1,
    }


def test_summarize_pages_handles_an_empty_document() -> None:
    assert summarize_pages([]) == {
        "page_count": 0,
        "empty_pages": 0,
        "characters": 0,
        "words": 0,
        "replacement_characters": 0,
        "control_characters": 0,
    }


def test_manual_review_template_lists_each_parser_for_each_paper(
    tmp_path,
) -> None:
    template_path = tmp_path / "manual_review.csv"

    _write_manual_review_template(template_path)

    with template_path.open(encoding="utf-8", newline="") as review_file:
        rows = list(csv.DictReader(review_file))

    assert len(rows) == len(SAMPLE_PAPER_IDS) * len(PARSER_NAMES)
    assert rows[0]["paper_id"] == SAMPLE_PAPER_IDS[0]
    assert rows[0]["parser"] == PARSER_NAMES[0]
    assert all(field in rows[0] for field in MANUAL_REVIEW_FIELDS)


def test_manual_review_template_preserves_scores_and_adds_new_parser(tmp_path) -> None:
    template_path = tmp_path / "manual_review.csv"
    with template_path.open("w", encoding="utf-8", newline="") as review_file:
        writer = csv.DictWriter(
            review_file,
            fieldnames=("paper_id", "parser", *MANUAL_REVIEW_FIELDS),
        )
        writer.writeheader()
        writer.writerow(
            {
                "paper_id": SAMPLE_PAPER_IDS[0],
                "parser": PARSER_NAMES[0],
                "two_column_order_1_to_5": "4",
                "notes": "Existing human note",
            }
        )

    _write_manual_review_template(template_path)

    with template_path.open(encoding="utf-8", newline="") as review_file:
        rows = list(csv.DictReader(review_file))

    assert len(rows) == len(SAMPLE_PAPER_IDS) * len(PARSER_NAMES)
    saved_score = next(
        row
        for row in rows
        if row["paper_id"] == SAMPLE_PAPER_IDS[0] and row["parser"] == PARSER_NAMES[0]
    )
    assert saved_score["two_column_order_1_to_5"] == "4"
    assert saved_score["notes"] == "Existing human note"
    assert any(row["parser"] == "pdfplumber-layout" for row in rows)
