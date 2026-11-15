"""Cross-encoder reranking for a bounded set of retrieved passages."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from neuralnotes.chunking import Chunk

DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"
DEFAULT_RERANKER_BATCH_SIZE = 16


class _CrossEncoderModel(Protocol):
    """Subset of the Sentence Transformers CrossEncoder API used here."""

    def predict(
        self,
        sentences: Sequence[tuple[str, str]],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> Iterable[float]: ...


@dataclass(frozen=True, slots=True)
class RerankedHit:
    """A candidate chunk and its cross-encoder relevance score."""

    chunk: Chunk
    score: float


class CrossEncoderReranker:
    """Reorder candidate passages using a sentence-transformers cross-encoder."""

    def __init__(
        self,
        model_name: str = DEFAULT_RERANKER_MODEL,
        *,
        batch_size: int = DEFAULT_RERANKER_BATCH_SIZE,
        device: str | None = None,
        model: _CrossEncoderModel | None = None,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name must not be empty.")
        if (
            isinstance(batch_size, bool)
            or not isinstance(batch_size, int)
            or batch_size < 1
        ):
            raise ValueError("batch_size must be a positive integer.")
        if device is not None and not device.strip():
            raise ValueError("device must not be empty when provided.")

        self.model_name = model_name
        self.batch_size = batch_size
        self.device = device
        self._model = model

    def rerank(
        self,
        query: str,
        candidates: Sequence[Chunk],
        *,
        top_k: int,
    ) -> tuple[RerankedHit, ...]:
        """Return the highest-scored candidates, preserving input order on ties."""
        if not query.strip():
            raise ValueError("query must not be empty or whitespace.")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer.")
        candidate_list = tuple(candidates)
        if not candidate_list:
            return ()

        pairs = tuple((query, chunk.text) for chunk in candidate_list)
        model_scores = self._get_model().predict(
            pairs, batch_size=self.batch_size, show_progress_bar=False
        )
        scores = self._validate_scores(model_scores, expected_count=len(candidate_list))
        ranked = sorted(
            enumerate(zip(candidate_list, scores, strict=True)),
            key=lambda item: (-item[1][1], item[0]),
        )
        return tuple(
            RerankedHit(chunk=chunk, score=score)
            for _, (chunk, score) in ranked[:top_k]
        )

    def warm_up(self) -> None:
        """Load the model and run one unmeasured pair before timed evaluation."""
        self._get_model().predict(
            (("warm-up query", "warm-up passage"),),
            batch_size=1,
            show_progress_bar=False,
        )

    def _get_model(self) -> _CrossEncoderModel:
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RuntimeError(
                    "Install the optional embeddings dependencies to load the reranker."
                ) from exc

            model_options = {} if self.device is None else {"device": self.device}
            self._model = CrossEncoder(self.model_name, **model_options)
        return self._model

    @staticmethod
    def _validate_scores(
        scores: Iterable[float], *, expected_count: int
    ) -> tuple[float, ...]:
        try:
            values = tuple(float(score) for score in scores)
        except (TypeError, ValueError) as exc:
            raise ValueError("The cross-encoder returned invalid scores.") from exc
        if len(values) != expected_count:
            raise ValueError("The cross-encoder returned an unexpected score count.")
        if not all(isfinite(score) for score in values):
            raise ValueError("The cross-encoder returned non-finite scores.")
        return values
