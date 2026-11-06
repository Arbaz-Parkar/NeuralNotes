"""Local content-addressed cache for document and query embeddings."""

from __future__ import annotations

import json
import math
import sqlite3
from collections.abc import Mapping, Sequence
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from typing import Literal

from neuralnotes.embeddings.protocols import EmbeddingModel, EmbeddingVector

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EMBEDDING_CACHE_PATH = PROJECT_ROOT / "data" / "cache" / "embeddings.sqlite3"
EmbeddingKind = Literal["document", "query"]
SQLITE_QUERY_BATCH_SIZE = 400


class SQLiteEmbeddingCache:
    """Store normalized embedding vectors in an ignored local SQLite file."""

    def __init__(self, path: Path = DEFAULT_EMBEDDING_CACHE_PATH) -> None:
        self._path = path

    def get_many(
        self,
        model_name: str,
        embedding_kind: EmbeddingKind,
        texts: Sequence[str],
    ) -> dict[str, EmbeddingVector]:
        """Return cached vectors for matching model, role, and text hashes."""
        unique_texts = tuple(dict.fromkeys(texts))
        if not unique_texts:
            return {}

        text_hashes = tuple(dict.fromkeys(_content_hash(text) for text in unique_texts))
        vectors_by_hash: dict[str, EmbeddingVector] = {}
        self._path.parent.mkdir(parents=True, exist_ok=True)

        with closing(sqlite3.connect(self._path, timeout=30)) as connection:
            with connection:
                connection.execute(_CREATE_CACHE_TABLE)
                for offset in range(0, len(text_hashes), SQLITE_QUERY_BATCH_SIZE):
                    batch = text_hashes[offset : offset + SQLITE_QUERY_BATCH_SIZE]
                    placeholders = ", ".join("?" for _ in batch)
                    rows = connection.execute(
                        "SELECT content_hash, vector_json FROM embeddings "
                        "WHERE model_name = ? AND embedding_kind = ? "
                        f"AND content_hash IN ({placeholders})",
                        (model_name, embedding_kind, *batch),
                    ).fetchall()
                    for content_hash, vector_json in rows:
                        vector = _decode_vector(vector_json)
                        if vector is not None:
                            vectors_by_hash[content_hash] = vector

        return {
            text: vectors_by_hash[content_hash]
            for text in unique_texts
            if (content_hash := _content_hash(text)) in vectors_by_hash
        }

    def set_many(
        self,
        model_name: str,
        embedding_kind: EmbeddingKind,
        embeddings: Mapping[str, EmbeddingVector],
    ) -> None:
        """Persist vectors, replacing malformed or stale rows with the same key."""
        if not embeddings:
            return

        rows = tuple(
            (
                model_name,
                embedding_kind,
                _content_hash(text),
                _encode_vector(vector),
            )
            for text, vector in embeddings.items()
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)

        with closing(sqlite3.connect(self._path, timeout=30)) as connection:
            with connection:
                connection.execute(_CREATE_CACHE_TABLE)
                connection.executemany(
                    "INSERT INTO embeddings "
                    "(model_name, embedding_kind, content_hash, vector_json) "
                    "VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(model_name, embedding_kind, content_hash) "
                    "DO UPDATE SET vector_json = excluded.vector_json",
                    rows,
                )


class CachedEmbeddingModel:
    """Wrap an embedding model and cache vectors by model and input content."""

    def __init__(
        self,
        model: EmbeddingModel,
        cache: SQLiteEmbeddingCache | None = None,
    ) -> None:
        if not model.model_name.strip():
            raise ValueError("The embedding model name must not be empty.")
        self._model = model
        self._cache = cache or SQLiteEmbeddingCache()

    @property
    def model_name(self) -> str:
        """Return the wrapped model identifier used in cache keys."""
        return self._model.model_name

    @property
    def dimension(self) -> int:
        """Return the wrapped model's vector dimension."""
        return self._model.dimension

    def embed_documents(self, texts: Sequence[str]) -> tuple[EmbeddingVector, ...]:
        """Reuse cached document vectors and embed each unique miss once."""
        documents = tuple(texts)
        _validate_texts(documents)
        if not documents:
            return ()

        unique_documents = tuple(dict.fromkeys(documents))
        cached = self._cache.get_many(self.model_name, "document", unique_documents)
        dimension = self.dimension if cached else None
        valid_cached = {
            text: vector
            for text, vector in cached.items()
            if dimension is not None and len(vector) == dimension
        }
        missing = tuple(text for text in unique_documents if text not in valid_cached)

        if missing:
            embedded = tuple(self._model.embed_documents(missing))
            if len(embedded) != len(missing):
                raise ValueError("The embedder must return one vector for every text.")
            dimension = self.dimension
            if any(len(vector) != dimension for vector in embedded):
                raise ValueError(
                    "The embedder returned a vector with an unexpected dimension."
                )
            new_vectors = dict(zip(missing, embedded, strict=True))
            self._cache.set_many(self.model_name, "document", new_vectors)
            valid_cached.update(new_vectors)

        return tuple(valid_cached[text] for text in documents)

    def embed_query(self, text: str) -> EmbeddingVector:
        """Reuse a cached query vector or compute and store it."""
        _validate_texts((text,))
        cached = self._cache.get_many(self.model_name, "query", (text,)).get(text)
        if cached is not None and len(cached) == self.dimension:
            return cached

        vector = self._model.embed_query(text)
        if len(vector) != self.dimension:
            raise ValueError(
                "The embedder returned a vector with an unexpected dimension."
            )
        self._cache.set_many(self.model_name, "query", {text: vector})
        return vector


_CREATE_CACHE_TABLE = """
CREATE TABLE IF NOT EXISTS embeddings (
    model_name TEXT NOT NULL,
    embedding_kind TEXT NOT NULL CHECK (embedding_kind IN ('document', 'query')),
    content_hash TEXT NOT NULL,
    vector_json TEXT NOT NULL,
    PRIMARY KEY (model_name, embedding_kind, content_hash)
)
"""


def _content_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _encode_vector(vector: EmbeddingVector) -> str:
    if not vector or not all(math.isfinite(value) for value in vector):
        raise ValueError("Cached embeddings must contain finite values.")
    norm = math.sqrt(sum(value * value for value in vector))
    if not math.isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
        raise ValueError("Cached embeddings must be normalized.")
    return json.dumps(vector, separators=(",", ":"))


def _decode_vector(vector_json: str) -> EmbeddingVector | None:
    try:
        values = json.loads(vector_json)
        if not isinstance(values, list):
            return None
        vector = tuple(float(value) for value in values)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None

    if not vector or not all(math.isfinite(value) for value in vector):
        return None
    norm = math.sqrt(sum(value * value for value in vector))
    if not math.isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
        return None
    return vector


def _validate_texts(texts: Sequence[str]) -> None:
    if any(not text.strip() for text in texts):
        raise ValueError("Embedding input text must not be empty or whitespace.")
