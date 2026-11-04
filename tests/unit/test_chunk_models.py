"""Tests for chunk metadata and stable chunk identifiers."""

from dataclasses import replace

import pytest

from neuralnotes.chunking import Chunk, make_chunk_id


def _make_chunk(**changes: object) -> Chunk:
    values: dict[str, object] = {
        "chunk_id": "chunk-1",
        "document_id": "document-1",
        "text": "A source passage.",
        "page_number": 1,
        "chunk_index": 0,
        "start_char": 0,
        "end_char": 17,
        "token_count": 4,
        "strategy": "fixed_size",
        "section_path": (),
    }
    values.update(changes)
    return Chunk(**values)  # type: ignore[arg-type]


def test_make_chunk_id_is_stable_for_same_content_and_position() -> None:
    first = make_chunk_id(
        document_id="document-1",
        page_number=2,
        chunk_index=3,
        start_char=40,
        end_char=80,
        strategy="fixed_size",
        text="A source passage.",
    )
    second = make_chunk_id(
        document_id="document-1",
        page_number=2,
        chunk_index=3,
        start_char=40,
        end_char=80,
        strategy="fixed_size",
        text="A source passage.",
    )

    assert first == second
    assert len(first) == 64


def test_make_chunk_id_changes_when_source_position_changes() -> None:
    original = make_chunk_id(
        document_id="document-1",
        page_number=2,
        chunk_index=3,
        start_char=40,
        end_char=80,
        strategy="fixed_size",
        text="A source passage.",
    )
    moved = make_chunk_id(
        document_id="document-1",
        page_number=2,
        chunk_index=4,
        start_char=80,
        end_char=120,
        strategy="fixed_size",
        text="A source passage.",
    )

    assert original != moved


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("text", "   ", "Chunk text must not be empty"),
        ("page_number", 0, "page numbers start at 1"),
        ("chunk_index", -1, "indexes start at 0"),
        ("start_char", -1, "character offsets"),
        ("end_char", 0, "character offsets"),
        ("token_count", 0, "token counts must be positive"),
        ("strategy", "unknown", "Unsupported chunk strategy"),
    ],
)
def test_chunk_rejects_invalid_metadata(
    field: str,
    value: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(_make_chunk(), **{field: value})
