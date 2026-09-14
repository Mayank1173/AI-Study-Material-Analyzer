"""CORS behavior tests.

These use a freshly built application so the CORS middleware picks up the
environment under test.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings


@pytest.fixture()
def cors_app(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
    get_settings.cache_clear()

    from main import create_app

    app = create_app()
    with TestClient(app) as client:
        yield client

    get_settings.cache_clear()


def test_configured_localhost_origin_allowed(cors_app):
    response = cors_app.get(
        "/", headers={"Origin": "http://localhost:5173"}
    )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin")
        == "http://localhost:5173"
    )


def test_configured_127_origin_allowed(cors_app):
    response = cors_app.get(
        "/", headers={"Origin": "http://127.0.0.1:5173"}
    )
    assert (
        response.headers.get("access-control-allow-origin")
        == "http://127.0.0.1:5173"
    )


def test_unconfigured_origin_not_allowed(cors_app):
    response = cors_app.get(
        "/", headers={"Origin": "http://evil.example.com"}
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_preflight_allowed_origin(cors_app):
    response = cors_app.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin")
        == "http://localhost:5173"
    )
    assert "POST" in response.headers.get("access-control-allow-methods", "")
    assert (
        response.headers.get("access-control-allow-credentials") == "true"
    )


def test_preflight_unconfigured_origin_rejected(cors_app):
    response = cors_app.options(
        "/api/auth/login",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_no_origin_gets_no_cors_headers(cors_app):
    response = cors_app.get("/")
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers