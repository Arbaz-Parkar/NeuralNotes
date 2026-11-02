"""Tests for the HTTP API."""

from fastapi.testclient import TestClient

from neuralnotes.api import app


def test_health_endpoint_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
