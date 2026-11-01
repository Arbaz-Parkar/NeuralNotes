"""Application-level exceptions shared across NeuralNotes layers."""


class NeuralNotesError(Exception):
    """Base class for errors the application can handle explicitly."""


class ConfigurationError(NeuralNotesError):
    """Raised when application configuration is missing or invalid."""


class InvalidRequestError(NeuralNotesError):
    """Raised when a caller provides an invalid request."""


class ResourceNotFoundError(NeuralNotesError):
    """Raised when a requested document or other resource does not exist."""


class ExternalServiceError(NeuralNotesError):
    """Raised when a required external service fails or is unavailable."""
