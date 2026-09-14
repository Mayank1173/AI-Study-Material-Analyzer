"""Health/liveness/database/readiness endpoint tests.

The database check is monkeypatched so these tests never touch a real
PostgreSQL instance.
"""
import pytest

from app.api.routes import health as health_routes


@pytest.fixture()
def db_up(monkeypatch):
    monkeypatch.setattr(health_routes, "check_database_health", lambda: True)
    return True


@pytest.fixture()
def db_down(monkeypatch):
    monkeypatch.setattr(health_routes, "check_database_health", lambda: False)
    return False


def test_liveness_always_healthy(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_database_health_up(client, db_up):
    response = client.get("/health/database")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "database": "connected"}


def test_database_health_down(client, db_down):
    response = client.get("/health/database")
    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy", "database": "unavailable"}


def test_readiness_up(client, db_up):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "connected"}


def test_readiness_down(client, db_down):
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "unavailable"}


def test_liveness_does_not_depend_on_database(client, db_down):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"