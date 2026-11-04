"""Fast Hugging Face tokenizer adapter with character offset mappings."""

from collections.abc import Mapping
from typing import Protocol

from neuralnotes.chunking.models import TokenSpan

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class _FastTokenizer(Protocol):
    """Subset of the Hugging Face fast tokenizer interface used here."""

    is_fast: bool

    def __call__(
        self,
        text: str,
        *,
        add_special_tokens: bool,
        return_offsets_mapping: bool,
        truncation: bool,
    ) -> Mapping[str, object]: ...


class HuggingFaceOffsetTokenizer:
    """Adapt a fast Hugging Face tokenizer to the chunker's span protocol."""

    def __init__(self, tokenizer: _FastTokenizer) -> None:
        if not tokenizer.is_fast:
            raise ValueError("A fast tokenizer is required for character offsets.")
        self._tokenizer = tokenizer

    @classmethod
    def from_pretrained(
        cls,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
    ) -> "HuggingFaceOffsetTokenizer":
        """Load a model tokenizer on demand without importing Transformers globally."""
        if not model_name.strip():
            raise ValueError("model_name must not be empty.")

        try:
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional embeddings dependencies to load this tokenizer."
            ) from exc

        tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        return cls(tokenizer)

    def token_spans(self, text: str) -> tuple[TokenSpan, ...]:
        """Return ordered, end-exclusive character spans for tokens in ``text``."""
        encoding = self._tokenizer(
            text,
            add_special_tokens=False,
            return_offsets_mapping=True,
            truncation=False,
        )
        offsets = encoding.get("offset_mapping")
        if not isinstance(offsets, (list, tuple)):
            raise ValueError("Fast tokenizer did not return offset mappings.")

        spans: list[TokenSpan] = []
        previous_end = 0
        for offset in offsets:
            if not isinstance(offset, (list, tuple)) or len(offset) != 2:
                raise ValueError("Tokenizer returned a malformed offset mapping.")
            start_char, end_char = offset
            if not isinstance(start_char, int) or not isinstance(end_char, int):
                raise ValueError(
                    "Tokenizer offsets must be integer character positions."
                )
            if start_char == end_char == 0:
                continue
            if (
                start_char < previous_end
                or start_char < 0
                or end_char <= start_char
                or end_char > len(text)
            ):
                raise ValueError(
                    "Tokenizer offsets must be ordered, non-overlapping, "
                    "and within text."
                )
            spans.append(TokenSpan(start_char, end_char))
            previous_end = end_char

        return tuple(spans)
