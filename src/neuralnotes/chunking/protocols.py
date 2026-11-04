"""Interfaces for tokenization used by chunking strategies."""

from collections.abc import Sequence
from typing import Protocol

from neuralnotes.chunking.models import TokenSpan


class TokenSpanTokenizer(Protocol):
    """Provide ordered, non-overlapping character spans for text tokens."""

    def token_spans(self, text: str) -> Sequence[TokenSpan]:
        """Return zero-based, end-exclusive spans into the original text."""
