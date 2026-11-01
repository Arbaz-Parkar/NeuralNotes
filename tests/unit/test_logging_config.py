"""Tests for JSON logging configuration."""

import json
import logging
import sys

import pytest

from neuralnotes.logging_config import JsonFormatter, configure_logging


def test_json_formatter_includes_safe_fields_and_request_id() -> None:
    record = logging.LogRecord(
        name="neuralnotes.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="loaded %s",
        args=("settings",),
        exc_info=None,
    )
    record.created = 0.0
    record.request_id = "request-123"
    record.document_text = "private document text"

    payload = json.loads(JsonFormatter().format(record))

    assert payload == {
        "timestamp": "1970-01-01T00:00:00.000Z",
        "level": "INFO",
        "logger": "neuralnotes.test",
        "message": "loaded settings",
        "request_id": "request-123",
    }
    assert "document_text" not in payload


def test_json_formatter_includes_exception_traceback() -> None:
    try:
        raise RuntimeError("provider failed")
    except RuntimeError:
        record = logging.LogRecord(
            name="neuralnotes.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="request failed",
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(JsonFormatter().format(record))

    assert "RuntimeError: provider failed" in payload["exception"]


def test_configure_logging_sets_json_console_handler() -> None:
    root_logger = logging.getLogger()
    previous_handlers = root_logger.handlers.copy()
    previous_level = root_logger.level

    try:
        configure_logging("DEBUG")

        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)
        assert isinstance(root_logger.handlers[0].formatter, JsonFormatter)
    finally:
        root_logger.handlers[:] = previous_handlers
        root_logger.setLevel(previous_level)


def test_configure_logging_rejects_unknown_level() -> None:
    with pytest.raises(ValueError, match="Unknown logging level"):
        configure_logging("VERBOSE")
