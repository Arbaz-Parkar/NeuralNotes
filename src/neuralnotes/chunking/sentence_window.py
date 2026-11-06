"""Sentence-window chunk generation with bounded neighboring context."""

import re

from neuralnotes.chunking.models import Chunk, TokenSpan, make_chunk_id
from neuralnotes.chunking.protocols import TokenSpanTokenizer
from neuralnotes.parsers.models import ParsedDocument

_CLOSING_MARKS = "\"'”’)}]"
_OPENING_MARKS = "\"'“‘([{"
_ABBREVIATIONS = (
    "e.g.",
    "i.e.",
    "et al.",
    "etc.",
    "fig.",
    "eq.",
    "dr.",
    "mr.",
    "mrs.",
    "prof.",
    "vs.",
    "no.",
    "vol.",
    "inc.",
    "approx.",
)
_INITIAL_RE = re.compile(r"(?:^|\s)[A-Z]\.$")


class SentenceWindowChunker:
    """Create sentence-centered chunks with nearby sentences when they fit."""

    def __init__(
        self,
        tokenizer: TokenSpanTokenizer,
        *,
        context_sentences: int = 1,
        max_tokens: int = 100,
    ) -> None:
        if context_sentences < 0:
            raise ValueError("context_sentences must be non-negative.")
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1.")

        self._tokenizer = tokenizer
        self._context_sentences = context_sentences
        self._max_tokens = max_tokens

    def chunk(
        self,
        document: ParsedDocument,
        *,
        document_id: str,
    ) -> tuple[Chunk, ...]:
        """Chunk each page into bounded sentence windows with source offsets."""
        if not document_id.strip():
            raise ValueError("document_id must not be empty.")

        chunks: list[Chunk] = []
        chunk_index = 0

        for page in document.pages:
            spans = tuple(self._tokenizer.token_spans(page.text))
            self._validate_spans(page.text, spans)
            sentences = self._sentence_ranges(page.text, spans)
            seen_ranges: set[tuple[int, int]] = set()

            for sentence_index, (sentence_start, sentence_end) in enumerate(sentences):
                windows = self._windows_for_sentence(
                    sentences, sentence_index, sentence_start, sentence_end
                )
                for start_token, end_token in windows:
                    if (start_token, end_token) in seen_ranges:
                        continue
                    seen_ranges.add((start_token, end_token))
                    start_char = (
                        0 if start_token == 0 else spans[start_token].start_char
                    )
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
                                strategy="sentence_window",
                                text=chunk_text,
                            ),
                            document_id=document_id,
                            text=chunk_text,
                            page_number=page.page_number,
                            chunk_index=chunk_index,
                            start_char=start_char,
                            end_char=end_char,
                            token_count=end_token - start_token,
                            strategy="sentence_window",
                        )
                    )
                    chunk_index += 1

        return tuple(chunks)

    def _windows_for_sentence(
        self,
        sentences: tuple[tuple[int, int], ...],
        sentence_index: int,
        sentence_start: int,
        sentence_end: int,
    ) -> tuple[tuple[int, int], ...]:
        if sentence_end - sentence_start > self._max_tokens:
            return tuple(
                (start, min(start + self._max_tokens, sentence_end))
                for start in range(sentence_start, sentence_end, self._max_tokens)
            )

        start_token = sentence_start
        end_token = sentence_end
        left_available = True
        right_available = True

        for distance in range(1, self._context_sentences + 1):
            left_index = sentence_index - distance
            if left_available and left_index >= 0:
                candidate_start = sentences[left_index][0]
                if end_token - candidate_start <= self._max_tokens:
                    start_token = candidate_start
                else:
                    left_available = False

            right_index = sentence_index + distance
            if right_available and right_index < len(sentences):
                candidate_end = sentences[right_index][1]
                if candidate_end - start_token <= self._max_tokens:
                    end_token = candidate_end
                else:
                    right_available = False

        return ((start_token, end_token),)

    @classmethod
    def _sentence_ranges(
        cls,
        text: str,
        spans: tuple[TokenSpan, ...],
    ) -> tuple[tuple[int, int], ...]:
        if not spans:
            return ()

        ranges: list[tuple[int, int]] = []
        sentence_start = 0
        for boundary in range(1, len(spans)):
            if cls._is_sentence_boundary(text, spans, boundary):
                ranges.append((sentence_start, boundary))
                sentence_start = boundary
        ranges.append((sentence_start, len(spans)))
        return tuple(ranges)

    @staticmethod
    def _is_sentence_boundary(
        text: str,
        spans: tuple[TokenSpan, ...],
        token_boundary: int,
    ) -> bool:
        previous = spans[token_boundary - 1]
        following = spans[token_boundary]
        gap = text[previous.end_char : following.start_char]
        if not gap or not gap.isspace():
            return False

        previous_text = text[previous.start_char : previous.end_char].rstrip()
        terminal = previous_text.rstrip(_CLOSING_MARKS)
        if not terminal or terminal[-1] not in ".!?":
            return False

        next_text = text[following.start_char : following.end_char].lstrip(
            _OPENING_MARKS
        )
        next_character = next_text[0] if next_text else ""
        if not (next_character.isupper() or next_character.isdigit()):
            return False

        if terminal.endswith("."):
            context_start = max(0, token_boundary - 4)
            context = text[spans[context_start].start_char : previous.end_char]
            normalized_context = context.casefold().rstrip(_CLOSING_MARKS)
            if any(normalized_context.endswith(item) for item in _ABBREVIATIONS):
                return False
            if _INITIAL_RE.search(context) is not None:
                return False

        return True

    @staticmethod
    def _validate_spans(text: str, spans: tuple[TokenSpan, ...]) -> None:
        previous_end = 0
        for span in spans:
            if span.start_char < previous_end or span.end_char > len(text):
                raise ValueError(
                    "Tokenizer spans must be ordered, non-overlapping, and within text."
                )
            previous_end = span.end_char
