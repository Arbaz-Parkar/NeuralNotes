"""Tests for content-addressed document and query embedding reuse."""

import sqlite3
from collections.abc import Sequence
from pathlib import Path

import pytest

from neuralnotes.embeddings import (
    CachedEmbeddingModel,
    EmbeddingVector,
    SQLiteEmbeddingCache,
)


class FakeEmbeddingModel:
    dimension = 2

    def __init__(self, model_name: str = "fake/model") -> None:
        self.model_name = model_name
        self.document_batches: list[tuple[str, ...]] = []
        self.query_texts: list[str] = []

    def embed_documents(
        self,
        texts: Sequence[str],
    ) -> tuple[EmbeddingVector, ...]:
        batch = tuple(texts)
        self.document_batches.append(batch)
        return tuple((0.6, 0.8) for _ in batch)

    def embed_query(self, text: str) -> EmbeddingVector:
        self.query_texts.append(text)
        return (0.6, 0.8)


def test_cached_model_reuses_unique_documents_and_preserves_order(
    tmp_path: Path,
) -> None:
    model = FakeEmbeddingModel()
    embedder = CachedEmbeddingModel(model, SQLiteEmbeddingCache(tmp_path / "cache.db"))

    first = embedder.embed_documents(("alpha", "beta", "alpha"))
    second = embedder.embed_documents(("beta", "alpha", "beta"))

    assert first == ((0.6, 0.8),) * 3
    assert second == ((0.6, 0.8),) * 3
    assert model.document_batches == [("alpha", "beta")]


def test_cached_model_persists_across_wrappers_and_separates_model_names(
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "cache.db"
    first_model = FakeEmbeddingModel("fake/model-a")
    first = CachedEmbeddingModel(first_model, SQLiteEmbeddingCache(cache_path))
    first.embed_documents(("repeated content",))

    same_model = FakeEmbeddingModel("fake/model-a")
    same_embedder = CachedEmbeddingModel(same_model, SQLiteEmbeddingCache(cache_path))
    same_embedder.embed_documents(("repeated content",))
    other_model = FakeEmbeddingModel("fake/model-b")
    other_embedder = CachedEmbeddingModel(other_model, SQLiteEmbeddingCache(cache_path))
    other_embedder.embed_documents(("repeated content",))

    assert same_model.document_batches == []
    assert other_model.document_batches == [("repeated content",)]


def test_cached_model_keeps_document_and_query_embeddings_separate(
    tmp_path: Path,
) -> None:
    model = FakeEmbeddingModel()
    embedder = CachedEmbeddingModel(model, SQLiteEmbeddingCache(tmp_path / "cache.db"))

    document_vector = embedder.embed_documents(("same text",))[0]
    query_vector = embedder.embed_query("same text")
    repeated_query_vector = embedder.embed_query("same text")

    assert document_vector == query_vector == repeated_query_vector
    assert model.document_batches == [("same text",)]
    assert model.query_texts == ["same text"]


def test_cached_model_recomputes_a_corrupt_cache_row(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.db"
    cache = SQLiteEmbeddingCache(cache_path)
    first_model = FakeEmbeddingModel()
    CachedEmbeddingModel(first_model, cache).embed_documents(("alpha",))

    with sqlite3.connect(cache_path) as connection:
        connection.execute("UPDATE embeddings SET vector_json = 'invalid'")

    second_model = FakeEmbeddingModel()
    vector = CachedEmbeddingModel(second_model, cache).embed_documents(("alpha",))

    assert vector == ((0.6, 0.8),)
    assert second_model.document_batches == [("alpha",)]


def test_cached_model_rejects_blank_text_without_calling_model(
    tmp_path: Path,
) -> None:
    model = FakeEmbeddingModel()
    embedder = CachedEmbeddingModel(model, SQLiteEmbeddingCache(tmp_path / "cache.db"))

    with pytest.raises(ValueError, match="must not be empty"):
        embedder.embed_documents((" ",))

    assert model.document_batches == []
