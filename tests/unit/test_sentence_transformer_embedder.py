"""Tests for the Sentence Transformers embedding adapter."""

import sys
from collections.abc import Iterable, Sequence
from types import ModuleType

import pytest

from neuralnotes.embeddings import SentenceTransformerEmbedder


class FakeSentenceTransformer:
    def __init__(
        self,
        *,
        dimension: int = 2,
        document_vectors: Iterable[Sequence[float]] | None = None,
        query_vector: Sequence[float] = (0.6, 0.8),
    ) -> None:
        self._dimension = dimension
        self.document_vectors = tuple(document_vectors or ((0.6, 0.8),))
        self.query_vector = query_vector
        self.document_call: tuple[tuple[str, ...], dict[str, object]] | None = None
        self.query_call: tuple[tuple[str, ...], dict[str, object]] | None = None

    def get_embedding_dimension(self) -> int:
        return self._dimension

    def encode_document(
        self,
        inputs: Sequence[str],
        **options: object,
    ) -> Iterable[Sequence[float]]:
        self.document_call = (tuple(inputs), options)
        return self.document_vectors

    def encode_query(
        self,
        inputs: Sequence[str],
        **options: object,
    ) -> Iterable[Sequence[float]]:
        self.query_call = (tuple(inputs), options)
        return tuple(self.query_vector for _ in inputs)


def test_embed_documents_returns_one_normalized_vector_per_input() -> None:
    model = FakeSentenceTransformer(document_vectors=((0.6, 0.8), (0.8, 0.6)))
    embedder = SentenceTransformerEmbedder(model=model, batch_size=7)

    vectors = embedder.embed_documents(("first passage", "second passage"))

    assert vectors == ((0.6, 0.8), (0.8, 0.6))
    assert embedder.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert embedder.dimension == 2
    assert model.document_call == (
        ("first passage", "second passage"),
        {
            "batch_size": 7,
            "show_progress_bar": False,
            "convert_to_numpy": True,
            "normalize_embeddings": True,
        },
    )


def test_embed_query_uses_query_encoding_and_normalization() -> None:
    model = FakeSentenceTransformer()
    embedder = SentenceTransformerEmbedder(model=model)

    vector = embedder.embed_query("search for this")

    assert vector == (0.6, 0.8)
    assert model.query_call == (
        ("search for this",),
        {
            "show_progress_bar": False,
            "convert_to_numpy": True,
            "normalize_embeddings": True,
        },
    )


def test_empty_document_batch_returns_without_loading_the_model() -> None:
    embedder = SentenceTransformerEmbedder()

    assert embedder.embed_documents(()) == ()


@pytest.mark.parametrize(
    "options",
    [
        {"batch_size": 0},
        {"device": " "},
        {"model_name": " "},
    ],
)
def test_embedder_validates_configuration(options: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        SentenceTransformerEmbedder(**options)  # type: ignore[arg-type]


@pytest.mark.parametrize("text", ["", "  "])
def test_embedder_rejects_empty_document_text(text: str) -> None:
    embedder = SentenceTransformerEmbedder(model=FakeSentenceTransformer())

    with pytest.raises(ValueError, match="must not be empty"):
        embedder.embed_documents((text,))


def test_embedder_rejects_empty_query_text() -> None:
    embedder = SentenceTransformerEmbedder(model=FakeSentenceTransformer())

    with pytest.raises(ValueError, match="must not be empty"):
        embedder.embed_query(" ")


@pytest.mark.parametrize(
    "vectors",
    [
        ((0.6, 0.8),),
        ((0.6, 0.8, 0.0), (0.6, 0.8)),
        ((float("nan"), 0.8), (0.6, 0.8)),
        ((1.0, 1.0), (0.6, 0.8)),
    ],
)
def test_embedder_rejects_invalid_document_vectors(
    vectors: tuple[tuple[float, ...], ...],
) -> None:
    model = FakeSentenceTransformer(document_vectors=vectors)
    embedder = SentenceTransformerEmbedder(model=model)

    with pytest.raises(ValueError):
        embedder.embed_documents(("first", "second"))


def test_embedder_loads_the_model_lazily_and_honors_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}
    fake_model = FakeSentenceTransformer()

    class FakeSentenceTransformerLoader:
        def __new__(cls, model_name: str, **options: str) -> FakeSentenceTransformer:
            calls.update(model_name=model_name, **options)
            return fake_model

    fake_module = ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = FakeSentenceTransformerLoader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    embedder = SentenceTransformerEmbedder(
        model_name="example/model",
        device="cpu",
    )

    assert calls == {}
    assert embedder.embed_query("question") == (0.6, 0.8)
    assert calls == {"model_name": "example/model", "device": "cpu"}
