"""Embedding model interfaces and adapters."""

from neuralnotes.embeddings.protocols import EmbeddingModel, EmbeddingVector
from neuralnotes.embeddings.sentence_transformer import SentenceTransformerEmbedder

__all__ = ["EmbeddingModel", "EmbeddingVector", "SentenceTransformerEmbedder"]
