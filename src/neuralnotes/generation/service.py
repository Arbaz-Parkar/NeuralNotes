"""Orchestration and structural citation validation for grounded answers."""

from collections.abc import Sequence

from neuralnotes.generation.models import (
    CitedClaim,
    GroundedAnswer,
    RetrievedPassage,
)
from neuralnotes.generation.protocols import AnswerGenerator


def generate_grounded_answer(
    question: str,
    passages: Sequence[RetrievedPassage],
    generator: AnswerGenerator,
) -> GroundedAnswer:
    """Generate claims and resolve every citation against supplied passages.

    This validates citation membership and source coordinates. It does not prove
    that a passage semantically entails a claim; that requires separate review
    or an evaluated entailment method.
    """
    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("question must contain at least one non-whitespace character.")

    passage_list = tuple(passages)
    passages_by_id = {passage.chunk_id: passage for passage in passage_list}
    if len(passages_by_id) != len(passage_list):
        raise ValueError("Retrieved passages must have unique chunk ids.")
    if not passage_list:
        return GroundedAnswer(answer="", abstained=True, claims=())

    draft = generator.generate(normalized_question, passage_list)
    if draft.abstained:
        return GroundedAnswer(answer="", abstained=True, claims=())

    cited_claims: list[CitedClaim] = []
    for claim in draft.claims:
        missing_ids = tuple(
            chunk_id for chunk_id in claim.citations if chunk_id not in passages_by_id
        )
        if missing_ids:
            raise ValueError(
                "Answer citations must refer to retrieved passages; unknown chunk ids: "
                f"{', '.join(missing_ids)}."
            )
        cited_claims.append(
            CitedClaim(
                text=claim.text,
                citations=tuple(
                    passages_by_id[chunk_id] for chunk_id in claim.citations
                ),
            )
        )

    return GroundedAnswer(
        answer=" ".join(claim.text.strip() for claim in draft.claims),
        abstained=False,
        claims=tuple(cited_claims),
    )
