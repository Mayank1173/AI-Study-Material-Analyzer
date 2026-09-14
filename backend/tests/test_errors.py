"""Consistent error-response format tests."""
import uuid

import pytest
from sqlalchemy.exc import OperationalError


def _error_body(response):
    return response.json().get("error", {})


def test_missing_course_returns_404_envelope(client, teacher_auth):
    _, headers = teacher_auth
    response = client.get(f"/api/courses/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404
    error = _error_body(response)
    assert error["code"] == "RESOURCE_NOT_FOUND"
    assert len(error["message"]) > 0
    assert "detail" in response.json()


def test_missing_material_returns_404_envelope(client, teacher_auth):
    _, headers = teacher_auth
    response = client.get(f"/api/materials/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404
    assert _error_body(response)["code"] == "RESOURCE_NOT_FOUND"


def test_unauthorized_returns_401_envelope(client):
    response = client.get("/api/courses")
    assert response.status_code == 401
    assert _error_body(response)["code"] == "UNAUTHORIZED"


def test_forbidden_returns_403_envelope(client, student_auth):
    _, headers = student_auth
    response = client.post(
        "/api/courses",
        json={"name": "Databases", "code": "CS301"},
        headers=headers,
    )
    assert response.status_code == 403
    assert _error_body(response)["code"] == "FORBIDDEN"


def test_duplicate_resource_returns_409_envelope(client, teacher_auth):
    _, headers = teacher_auth

    def create():
        return client.post(
            "/api/courses",
            json={"name": "Databases", "code": "CS301"},
            headers=headers,
        )

    assert create().status_code == 201
    response = create()
    assert response.status_code == 409
    assert _error_body(response)["code"] == "CONFLICT"


def test_validation_error_returns_422_envelope(client):
    response = client.post(
        "/api/auth/register",
        json={"name": "", "email": "not-an-email", "password": "short"},
    )
    assert response.status_code == 422
    assert _error_body(response)["code"] == "VALIDATION_ERROR"
    # FastAPI's standard validation detail structure is preserved.
    assert isinstance(response.json()["detail"], list)


def test_invalid_material_status_rejected(client, teacher_auth):
    _, headers = teacher_auth
    course_id = client.post(
        "/api/courses",
        json={"name": "Databases", "code": "CS301"},
        headers=headers,
    ).json()["id"]
    response = client.post(
        "/api/materials",
        json={
            "course_id": course_id,
            "title": "Notes",
            "material_type": "notes",
            "status": "not-a-real-status",
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert _error_body(response)["code"] == "VALIDATION_ERROR"


def test_error_responses_do_not_leak_secrets(client, teacher_auth):
    _, headers = teacher_auth

    responses = [
        client.get(f"/api/courses/{uuid.uuid4()}", headers=headers),
        client.get("/api/courses"),
        client.post(
            "/api/courses",
            json={"name": "Databases", "code": "CS301"},
            headers=headers,
        ),
    ]
    # Force a 409 by re-creating the same course twice.
    client.post(
        "/api/courses",
        json={"name": "Databases", "code": "CS301"},
        headers=headers,
    )
    responses.append(
        client.post(
            "/api/courses",
            json={"name": "Databases", "code": "CS301"},
            headers=headers,
        )
    )

    for response in responses:
        text = response.text.lower()
        assert "password_hash" not in text
        assert "password" not in text
        assert "traceback" not in text
        assert "secret" not in text
        assert "sqlalchemy" not in text


def test_database_failure_returns_json_envelope(client, teacher_auth, monkeypatch):
    from app.api.routes import courses as course_routes

    def _boom(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("db unreachable"))

    monkeypatch.setattr(course_routes.course_service, "list_courses", _boom)

    _, headers = teacher_auth
    response = client.get("/api/courses", headers=headers)
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert body["detail"] == "Internal server error"
    text = response.text.lower()
    assert "traceback" not in text
    assert "db unreachable" not in text
    assert "sqlalchemy" not in text
    assert "password" not in text


def test_storage_failure_returns_json_envelope(client, teacher_auth, monkeypatch):
    from app.api.routes import materials as material_routes

    def _boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(
        material_routes.study_material_service, "get_study_material", _boom
    )

    _, headers = teacher_auth
    response = client.get(f"/api/materials/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    text = response.text.lower()
    assert "disk full" not in text
    assert "traceback" not in text