"""Recursive, separator-aware chunk generation."""

import re

from neuralnotes.chunking.models import Chunk, TokenSpan, make_chunk_id
from neuralnotes.chunking.protocols import TokenSpanTokenizer
from neuralnotes.parsers.models import ParsedDocument

_SENTENCE_END = re.compile(r"[.!?][\"'”’)}\]]*$")


class RecursiveChunker:
    """Prefer paragraph, line, sentence, and whitespace boundaries in that order."""

    def __init__(
        self,
        tokenizer: TokenSpanTokenizer,
        *,
        chunk_size: int = 100,
        overlap: int = 20,
    ) -> None:
        if chunk_size < 1:
            raise ValueError("chunk_size must be at least 1.")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be non-negative and less than chunk_size.")

        self._tokenizer = tokenizer
        self._chunk_size = chunk_size
        self._overlap = overlap

    def chunk(
        self,
        document: ParsedDocument,
        *,
        document_id: str,
    ) -> tuple[Chunk, ...]:
        """Split pages near structural boundaries while respecting the token limit."""
        if not document_id.strip():
            raise ValueError("document_id must not be empty.")

        chunks: list[Chunk] = []
        chunk_index = 0

        for page in document.pages:
            spans = tuple(self._tokenizer.token_spans(page.text))
            self._validate_spans(page.text, spans)
            start_token = 0

            while start_token < len(spans):
                max_end_token = min(start_token + self._chunk_size, len(spans))
                end_token = self._choose_end_token(
                    page.text, spans, start_token, max_end_token
                )
                start_char = 0 if start_token == 0 else spans[start_token].start_char
                end_char = (
                    len(page.text)
                    if end_token == len(spans)
                    else spans[end_token].start_char
                )
                chunk_text = page.text[start_char:end_char]
                chunks.append(
                    Chunk(
                        chunk_id=make_chunk_id(
                            document_id=document_id,
                            page_number=page.page_number,
                            chunk_index=chunk_index,
                            start_char=start_char,
                            end_char=end_char,
                            strategy="recursive",
                            text=chunk_text,
                        ),
                        document_id=document_id,
                        text=chunk_text,
                        page_number=page.page_number,
                        chunk_index=chunk_index,
                        start_char=start_char,
                        end_char=end_char,
                        token_count=end_token - start_token,
                        strategy="recursive",
                    )
                )
                chunk_index += 1

                if end_token == len(spans):
                    break
                start_token = max(start_token + 1, end_token - self._overlap)

        return tuple(chunks)

    def _choose_end_token(
        self,
        text: str,
        spans: tuple[TokenSpan, ...],
        start_token: int,
        max_end_token: int,
    ) -> int:
        """Choose the strongest available boundary without making tiny chunks."""
        if max_end_token == len(spans):
            return max_end_token

        minimum_end_token = min(
            max_end_token,
            start_token + max(self._overlap + 1, self._chunk_size // 2),
        )
        for boundary_priority in range(4):
            candidates = [
                token_boundary
                for token_boundary in range(minimum_end_token, max_end_token + 1)
                if self._boundary_priority(text, spans, token_boundary)
                == boundary_priority
            ]
            if candidates:
                return candidates[-1]

        return max_end_token

    @staticmethod
    def _boundary_priority(
        text: str,
        spans: tuple[TokenSpan, ...],
        token_boundary: int,
    ) -> int | None:
        if token_boundary < 1 or token_boundary >= len(spans):
            return None

        previous = spans[token_boundary - 1]
        following = spans[token_boundary]
        gap = text[previous.end_char : following.start_char]
        if "\n\n" in gap:
            return 0
        if "\n" in gap or "\r" in gap:
            return 1
        if _SENTENCE_END.search(text[previous.start_char : previous.end_char]):
            return 2
        if gap:
            return 3
        return None

    @staticmethod
    def _validate_spans(text: str, spans: tuple[TokenSpan, ...]) -> None:
        previous_end = 0
        for span in spans:
            if span.start_char < previous_end or span.end_char > len(text):
                raise ValueError(
                    "Tokenizer spans must be ordered, non-overlapping, and within text."
                )
            previous_end = span.end_char
