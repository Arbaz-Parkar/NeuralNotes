"""Embedding model interfaces and adapters."""

from neuralnotes.embeddings.cache import CachedEmbeddingModel, SQLiteEmbeddingCache
from neuralnotes.embeddings.protocols import EmbeddingModel, EmbeddingVector
from neuralnotes.embeddings.sentence_transformer import SentenceTransformerEmbedder

__all__ = [
    "CachedEmbeddingModel",
    "EmbeddingModel",
    "EmbeddingVector",
    "SQLiteEmbeddingCache",
    "SentenceTransformerEmbedder",
]
