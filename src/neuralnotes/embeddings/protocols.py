"""Interfaces for document and query embedding models."""

from collections.abc import Sequence
from typing import Protocol, TypeAlias

EmbeddingVector: TypeAlias = tuple[float, ...]


class EmbeddingModel(Protocol):
    """Embed document batches and individual search queries."""

    @property
    def model_name(self) -> str:
        """Return the configured model identifier."""

    @property
    def dimension(self) -> int:
        """Return the number of values in each embedding vector."""

    def embed_documents(
        self,
        texts: Sequence[str],
    ) -> tuple[EmbeddingVector, ...]:
        """Return one normalized vector per document text."""

    def embed_query(self, text: str) -> EmbeddingVector:
        """Return a normalized vector for one search query."""
