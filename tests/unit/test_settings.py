"""Tests for environment-backed application settings."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from neuralnotes.settings import Settings


def _clear_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "NEURALNOTES_APP_NAME",
        "NEURALNOTES_ENVIRONMENT",
        "NEURALNOTES_LOG_LEVEL",
        "NEURALNOTES_DATABASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)


def test_settings_have_development_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_settings_environment(monkeypatch)

    settings = Settings(_env_file=None)

    assert settings.app_name == "NeuralNotes"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.database_url == (
        "postgresql+psycopg://neuralnotes:neuralnotes-local@127.0.0.1:5432/neuralnotes"
    )


def test_prefixed_environment_variables_override_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_settings_environment(monkeypatch)
    monkeypatch.setenv("NEURALNOTES_APP_NAME", "Notes Test")
    monkeypatch.setenv("NEURALNOTES_ENVIRONMENT", "test")
    monkeypatch.setenv("NEURALNOTES_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv(
        "NEURALNOTES_DATABASE_URL",
        "postgresql+psycopg://user:secret@localhost:5432/test_db",
    )

    settings = Settings(_env_file=None)

    assert settings.app_name == "Notes Test"
    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.database_url == (
        "postgresql+psycopg://user:secret@localhost:5432/test_db"
    )


def test_invalid_environment_value_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_settings_environment(monkeypatch)
    monkeypatch.setenv("NEURALNOTES_ENVIRONMENT", "staging")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_load_from_dotenv_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_settings_environment(monkeypatch)
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "NEURALNOTES_APP_NAME=Loaded from file\nNEURALNOTES_LOG_LEVEL=WARNING\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.app_name == "Loaded from file"
    assert settings.log_level == "WARNING"
