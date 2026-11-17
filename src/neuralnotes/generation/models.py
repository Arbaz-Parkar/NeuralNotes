"""Validated data models for answers grounded in retrieved passages."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RetrievedPassage(BaseModel):
    """A retrieved chunk with source coordinates suitable for citation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_offsets(self) -> "RetrievedPassage":
        """Require a non-empty, ordered source span."""
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be greater than start_char.")
        return self


class AnswerClaim(BaseModel):
    """One answer statement and the retrieved chunk ids supporting it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1)
    citations: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_claim(self) -> "AnswerClaim":
        """Reject blank claims and repeated citation ids."""
        if not self.text.strip():
            raise ValueError("claim text must not be blank.")
        if any(not chunk_id.strip() for chunk_id in self.citations):
            raise ValueError("citation chunk ids must not be blank.")
        if len(set(self.citations)) != len(self.citations):
            raise ValueError("claim citations must not contain duplicates.")
        return self


class DraftAnswer(BaseModel):
    """Provider output before citation ids are resolved to source passages."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    abstained: bool
    claims: tuple[AnswerClaim, ...] = ()

    @model_validator(mode="after")
    def validate_abstention(self) -> "DraftAnswer":
        """Require either cited claims or an explicit empty abstention."""
        if self.abstained and self.claims:
            raise ValueError("an abstaining draft must not contain claims.")
        if not self.abstained and not self.claims:
            raise ValueError("a non-abstaining draft must contain claims.")
        return self


class CitedClaim(BaseModel):
    """An answer claim with its citation ids resolved to source metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    citations: tuple[RetrievedPassage, ...] = Field(min_length=1)


class GroundedAnswer(BaseModel):
    """Final answer containing only claims with validated retrieved sources."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    answer: str
    abstained: bool
    claims: tuple[CitedClaim, ...] = ()

    @model_validator(mode="after")
    def validate_result(self) -> "GroundedAnswer":
        """Keep answer text, claims, and abstention state consistent."""
        if self.abstained and (self.answer or self.claims):
            raise ValueError(
                "an abstained answer must not contain answer text or claims."
            )
        if not self.abstained and (not self.answer.strip() or not self.claims):
            raise ValueError("a grounded answer must contain text and cited claims.")
        return self
