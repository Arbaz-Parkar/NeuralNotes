"""Tests for the shared application error hierarchy."""

import pytest

from neuralnotes.errors import (
    ConfigurationError,
    ExternalServiceError,
    InvalidRequestError,
    NeuralNotesError,
    ResourceNotFoundError,
)


@pytest.mark.parametrize(
    "error_type",
    [
        ConfigurationError,
        InvalidRequestError,
        ResourceNotFoundError,
        ExternalServiceError,
    ],
)
def test_specific_errors_share_base_and_preserve_message(
    error_type: type[NeuralNotesError],
) -> None:
    with pytest.raises(NeuralNotesError, match="expected failure"):
        raise error_type("expected failure")
