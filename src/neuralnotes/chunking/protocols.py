"""Interfaces for tokenization used by chunking strategies."""

from collections.abc import Sequence
from typing import Protocol

from neuralnotes.chunking.models import Chunk, TokenSpan
from neuralnotes.parsers.models import ParsedDocument


class Chunker(Protocol):
    """Split a parsed document into ordered source-aware chunks."""

    def chunk(
        self,
        document: ParsedDocument,
        *,
        document_id: str,
    ) -> tuple[Chunk, ...]:
        """Return chunks tied to the document's source positions."""


class TokenSpanTokenizer(Protocol):
    """Provide ordered, non-overlapping character spans for text tokens."""

    def token_spans(self, text: str) -> Sequence[TokenSpan]:
        """Return zero-based, end-exclusive spans into the original text."""
