"""In-memory cosine-similarity retrieval over stored chunk embeddings."""

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite, sqrt

from neuralnotes.chunking import Chunk
from neuralnotes.embeddings import EmbeddingVector


@dataclass(frozen=True, slots=True)
class DenseHit:
    """A source chunk and its cosine-similarity score."""

    chunk: Chunk
    score: float


class DenseIndex:
    """Rank chunks by cosine similarity using their persisted vectors."""

    def __init__(
        self,
        items: Iterable[tuple[Chunk, EmbeddingVector]],
    ) -> None:
        self._items = tuple(items)
        self._dimension: int | None = None
        seen_ids: set[str] = set()
        for chunk, vector in self._items:
            if chunk.chunk_id in seen_ids:
                raise ValueError(
                    f"Duplicate chunk id in dense input: {chunk.chunk_id}."
                )
            seen_ids.add(chunk.chunk_id)
            self._validate_vector(vector)
            if self._dimension is None:
                self._dimension = len(vector)
            elif len(vector) != self._dimension:
                raise ValueError(
                    "All indexed embedding vectors must have equal dimensions."
                )

    @property
    def document_count(self) -> int:
        """Return the number of indexed chunks."""
        return len(self._items)

    def search(
        self, query_vector: EmbeddingVector, *, top_k: int = 5
    ) -> tuple[DenseHit, ...]:
        """Return the highest cosine-similarity chunks in stable tie order."""
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer.")
        self._validate_vector(query_vector)
        if self._dimension is not None and len(query_vector) != self._dimension:
            raise ValueError("Query embedding dimension does not match the index.")
        if not self._items:
            return ()

        query_norm = sqrt(sum(value * value for value in query_vector))
        scored: list[tuple[float, int, Chunk]] = []
        for position, (chunk, vector) in enumerate(self._items):
            vector_norm = sqrt(sum(value * value for value in vector))
            score = sum(a * b for a, b in zip(query_vector, vector, strict=True))
            score /= query_norm * vector_norm
            scored.append((score, position, chunk))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return tuple(
            DenseHit(chunk=chunk, score=score) for score, _, chunk in scored[:top_k]
        )

    @staticmethod
    def _validate_vector(vector: EmbeddingVector) -> None:
        if not vector or any(not isfinite(value) for value in vector):
            raise ValueError("Embedding vectors must be non-empty and finite.")
        if not any(value != 0.0 for value in vector):
            raise ValueError("Embedding vectors must have a non-zero norm.")
