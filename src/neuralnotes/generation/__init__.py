"""Provider-neutral, citation-grounded answer generation contracts."""

from neuralnotes.generation.models import (
    AnswerClaim,
    CitedClaim,
    DraftAnswer,
    GroundedAnswer,
    RetrievedPassage,
)
from neuralnotes.generation.protocols import AnswerGenerator
from neuralnotes.generation.service import generate_grounded_answer

__all__ = [
    "AnswerClaim",
    "AnswerGenerator",
    "CitedClaim",
    "DraftAnswer",
    "GroundedAnswer",
    "RetrievedPassage",
    "generate_grounded_answer",
]
