"""Sentence Transformers adapter for normalized text embeddings."""

import math
from collections.abc import Iterable, Sequence
from typing import Protocol

from neuralnotes.embeddings.protocols import EmbeddingVector

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_BATCH_SIZE = 32


class _SentenceTransformerModel(Protocol):
    """Subset of the SentenceTransformer API used by this adapter."""

    def get_embedding_dimension(self) -> int | None: ...

    def encode_document(
        self,
        inputs: Sequence[str],
        *,
        batch_size: int,
        show_progress_bar: bool,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
    ) -> Iterable[Sequence[float]]: ...

    def encode_query(
        self,
        inputs: Sequence[str],
        *,
        show_progress_bar: bool,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
    ) -> Sequence[float]: ...


class SentenceTransformerEmbedder:
    """Generate normalized embeddings with a lazily loaded local model."""

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
        device: str | None = None,
        model: _SentenceTransformerModel | None = None,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name must not be empty.")
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1.")
        if device is not None and not device.strip():
            raise ValueError("device must not be empty when provided.")

        self._model_name = model_name
        self._batch_size = batch_size
        self._device = device
        self._model = model

    @property
    def model_name(self) -> str:
        """Return the configured model identifier."""
        return self._model_name

    @property
    def dimension(self) -> int:
        """Return the loaded model's embedding dimension."""
        dimension = self._get_model().get_embedding_dimension()
        if not isinstance(dimension, int) or dimension < 1:
            raise ValueError("The model did not report a valid embedding dimension.")
        return dimension

    def embed_documents(self, texts: Sequence[str]) -> tuple[EmbeddingVector, ...]:
        """Embed a batch of document passages as unit-length vectors."""
        documents = tuple(texts)
        self._validate_texts(documents)
        if not documents:
            return ()

        encoded = self._get_model().encode_document(
            documents,
            batch_size=self._batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return self._validate_matrix(encoded, expected_rows=len(documents))

    def embed_query(self, text: str) -> EmbeddingVector:
        """Embed one search query as a unit-length vector."""
        self._validate_texts((text,))
        encoded = self._get_model().encode_query(
            (text,),
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return self._validate_matrix(encoded, expected_rows=1)[0]

    def _get_model(self) -> _SentenceTransformerModel:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "Install the optional embeddings dependencies to load this model."
                ) from exc

            model_options = {} if self._device is None else {"device": self._device}
            self._model = SentenceTransformer(self._model_name, **model_options)
        return self._model

    @staticmethod
    def _validate_texts(texts: Sequence[str]) -> None:
        if any(not text.strip() for text in texts):
            raise ValueError("Embedding input text must not be empty or whitespace.")

    def _validate_matrix(
        self,
        matrix: object,
        *,
        expected_rows: int,
    ) -> tuple[EmbeddingVector, ...]:
        if isinstance(matrix, (str, bytes)) or not isinstance(matrix, Iterable):
            raise ValueError("The embedding model returned an invalid matrix.")

        vectors = tuple(self._validate_vector(row) for row in matrix)
        if len(vectors) != expected_rows:
            raise ValueError("The embedding model returned an unexpected row count.")
        return vectors

    def _validate_vector(self, values: object) -> EmbeddingVector:
        if isinstance(values, (str, bytes)) or not isinstance(values, Iterable):
            raise ValueError("The embedding model returned an invalid vector.")
        try:
            vector = tuple(float(value) for value in values)
        except (TypeError, ValueError) as exc:
            raise ValueError("Embedding values must be numeric.") from exc

        if len(vector) != self.dimension:
            raise ValueError("The embedding vector has an unexpected dimension.")
        if not all(math.isfinite(value) for value in vector):
            raise ValueError("Embedding values must be finite numbers.")
        norm = math.sqrt(sum(value * value for value in vector))
        if not math.isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
            raise ValueError(
                "The embedding model returned a vector that is not normalized."
            )
        return vector
