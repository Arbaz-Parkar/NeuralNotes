"""SQLAlchemy declarative base for persistence models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class that owns NeuralNotes database metadata."""
