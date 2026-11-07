"""A small in-memory BM25 index with an inverted term-frequency index."""

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from heapq import heappush, heapreplace
from math import isfinite, log

from neuralnotes.chunking import Chunk

_TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class BM25Hit:
    """One chunk and its BM25 relevance score."""

    chunk: Chunk
    score: float


class BM25Index:
    """Rank chunks with BM25 using a term-to-chunk inverted index."""

    def __init__(
        self,
        chunks: Iterable[Chunk],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if not isfinite(k1) or k1 <= 0:
            raise ValueError("k1 must be a finite number greater than zero.")
        if not isfinite(b) or not 0 <= b <= 1:
            raise ValueError("b must be a finite number between zero and one.")

        self._k1 = k1
        self._b = b
        self._chunks: list[Chunk] = []
        self._document_lengths: list[int] = []
        self._document_frequency: dict[str, int] = {}
        self._postings: dict[str, dict[int, int]] = {}
        seen_chunk_ids: set[str] = set()
        total_length = 0

        for document_index, chunk in enumerate(chunks):
            if chunk.chunk_id in seen_chunk_ids:
                raise ValueError(f"Duplicate chunk id in BM25 input: {chunk.chunk_id}.")
            seen_chunk_ids.add(chunk.chunk_id)
            self._chunks.append(chunk)

            term_frequencies = Counter(_tokenize(chunk.text))
            document_length = sum(term_frequencies.values())
            self._document_lengths.append(document_length)
            total_length += document_length

            for term, frequency in term_frequencies.items():
                self._postings.setdefault(term, {})[document_index] = frequency
                self._document_frequency[term] = (
                    self._document_frequency.get(term, 0) + 1
                )

        self._document_count = len(self._chunks)
        self._average_document_length = (
            total_length / self._document_count if self._document_count else 0.0
        )

    @property
    def document_count(self) -> int:
        """Return the number of indexed chunks."""
        return self._document_count

    def search(self, query: str, *, top_k: int = 5) -> tuple[BM25Hit, ...]:
        """Return at most ``top_k`` matching chunks in descending score order."""
        if top_k < 1:
            raise ValueError("top_k must be at least one.")

        query_terms = _tokenize(query)
        if not query_terms or not self._document_count:
            return ()

        candidate_indexes: set[int] = set()
        for term in query_terms:
            candidate_indexes.update(self._postings.get(term, ()))
        if not candidate_indexes:
            return ()

        idf: dict[str, float] = {}
        for term in set(query_terms):
            frequency = self._document_frequency.get(term)
            if frequency is not None:
                idf[term] = log(
                    1.0 + (self._document_count - frequency + 0.5) / (frequency + 0.5)
                )
        heap: list[tuple[float, int, int]] = []
        for document_index in candidate_indexes:
            document_length = self._document_lengths[document_index]
            length_norm = self._k1 * (
                1.0
                - self._b
                + self._b * document_length / self._average_document_length
            )
            score = 0.0
            for term in query_terms:
                frequency = self._postings.get(term, {}).get(document_index, 0)
                if frequency:
                    score += (
                        idf[term]
                        * frequency
                        * (self._k1 + 1.0)
                        / (frequency + length_norm)
                    )

            # Earlier input chunks win exact score ties.
            entry = (score, -document_index, document_index)
            if len(heap) < top_k:
                heappush(heap, entry)
            elif entry[:2] > heap[0][:2]:
                heapreplace(heap, entry)

        ranked = sorted(heap, reverse=True)
        return tuple(
            BM25Hit(chunk=self._chunks[index], score=score)
            for score, _, index in ranked
        )


def _tokenize(text: str) -> tuple[str, ...]:
    """Lowercase text and split it into Unicode word tokens."""
    return tuple(_TOKEN_PATTERN.findall(text.casefold()))
