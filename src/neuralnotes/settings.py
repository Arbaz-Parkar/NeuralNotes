"""Validated application settings loaded from the environment."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="NEURALNOTES_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "NeuralNotes"
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: str = Field(
        default=(
            "postgresql+psycopg://neuralnotes:"
            "neuralnotes-local@127.0.0.1:5432/neuralnotes"
        ),
        repr=False,
    )
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3.5:4b"
    ollama_timeout_seconds: float = Field(default=120.0, gt=0, le=600)
