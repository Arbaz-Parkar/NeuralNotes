"""Interfaces for replaceable answer-generation providers."""

from collections.abc import Sequence
from typing import Protocol

from neuralnotes.generation.models import DraftAnswer, RetrievedPassage


class AnswerGenerator(Protocol):
    """Generate claim-level citation ids from a question and bounded context."""

    def generate(
        self,
        question: str,
        passages: Sequence[RetrievedPassage],
    ) -> DraftAnswer:
        """Return claims citing only chunk ids present in ``passages``."""
        ...
