import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models import User
from tests.conftest import (
    TEST_PASSWORD,
    auth_headers_for,
    login_user,
    make_auth_headers,
    make_db_user,
    register_user,
)

SETTINGS = get_settings()


def _expired_token(user_id: uuid.UUID) -> str:
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    return jwt.encode(
        {
            "sub": str(user_id),
            "exp": past,
            "iat": past - timedelta(minutes=1),
        },
        SETTINGS.jwt_secret_key,
        algorithm=SETTINGS.jwt_algorithm,
    )


def _db_user(db, email):
    return db.scalar(select(User).where(User.email == email))


def _make_course(client, headers, code="CS301"):
    return client.post(
        "/api/courses", json={"name": "Databases", "code": code}, headers=headers
    ).json()["id"]


@pytest.fixture()
def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_register_creates_normal_user(client, db):
    response = register_user(client, name="Ravi", email="ravi@example.com")
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ravi"
    assert body["email"] == "ravi@example.com"
    assert "role" not in body
    assert "id" in body
    uuid.UUID(body["id"])
    assert "password" not in body
    assert "password_hash" not in body


def test_register_hashes_password(client, db):
    register_user(client, name="Ravi", email="ravi@example.com")
    user = _db_user(db, "ravi@example.com")
    assert user is not None
    assert user.password_hash is not None
    assert user.password_hash != TEST_PASSWORD
    assert user.password_hash.startswith("$2")


def test_register_does_not_store_plaintext(client, db):
    register_user(client, name="Ravi", email="ravi@example.com")
    user = _db_user(db, "ravi@example.com")
    assert TEST_PASSWORD not in user.password_hash


def test_register_duplicate_email_rejected(client):
    assert register_user(client, email="dup@example.com").status_code == 201
    response = register_user(client, name="Other", email="dup@example.com")
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_register_default_role_is_student(client, db):
    register_user(client, name="Ravi", email="ravi@example.com")
    user = _db_user(db, "ravi@example.com")
    assert user.role == "student"


def test_register_ignores_role_claims(client, db):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Sneaky",
            "email": "sneaky@example.com",
            "password": TEST_PASSWORD,
            "role": "teacher",
        },
    )
    assert response.status_code == 201
    user = _db_user(db, "sneaky@example.com")
    assert user.role == "student"
    assert "role" not in response.json()


def test_register_validates_fields(client):
    response = client.post(
        "/api/auth/register",
        json={"name": "", "email": "bad", "password": "short"},
    )
    assert response.status_code == 422


def test_login_valid_credentials(client):
    register_user(client, name="Ravi", email="ravi@example.com")
    response = login_user(client, email="ravi@example.com")
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_rejected(client):
    register_user(client, name="Ravi", email="ravi@example.com")
    response = login_user(
        client, email="ravi@example.com", password="wrongpassword123"
    )
    assert response.status_code == 401


def test_login_unknown_account_rejected(client):
    response = login_user(client, email="nobody@example.com", password=TEST_PASSWORD)
    assert response.status_code == 401


def test_generic_error_for_unknown_and_wrong_password(client):
    register_user(client, name="Ravi", email="ravi@example.com")
    wrong_pass = login_user(
        client, email="ravi@example.com", password="wrongpassword123"
    )
    unknown = login_user(client, email="nobody@example.com", password=TEST_PASSWORD)
    assert wrong_pass.status_code == unknown.status_code == 401
    assert wrong_pass.json()["detail"] == unknown.json()["detail"]


def test_token_authenticates_request(client):
    register_user(client, name="Ravi", email="ravi@example.com")
    headers = make_auth_headers(client, email="ravi@example.com")
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "ravi@example.com"


def test_me_missing_token_returns_401(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_malformed_token_returns_401(client):
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401


def test_me_invalid_token_returns_401(client):
    token = jwt.encode(
        {"sub": str(uuid.uuid4())},
        "wrong-secret-key",
        algorithm="HS256",
    )
    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


def test_me_expired_token_returns_401(client):
    token = _expired_token(uuid.uuid4())
    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


def test_me_returns_public_fields(client):
    register_user(client, name="Ravi", email="ravi@example.com")
    headers = make_auth_headers(client, email="ravi@example.com")
    body = client.get("/api/auth/me", headers=headers).json()
    assert set(body.keys()) == {"id", "name", "email", "created_at"}
    assert "role" not in body
    assert "password" not in body
    assert "password_hash" not in body


def test_protected_endpoint_without_token_returns_401(client):
    assert client.get("/api/courses").status_code == 401
    assert client.get("/api/materials").status_code == 401


def test_any_authenticated_user_can_create_course(client, user_auth):
    _, headers = user_auth
    response = client.post(
        "/api/courses",
        json={"name": "Databases", "code": "CS301"},
        headers=headers,
    )
    assert response.status_code == 201


def test_any_user_can_upload_material(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _make_course(client, headers)
    response = client.post(
        "/api/materials/upload",
        data={
            "course_id": course_id,
            "title": "Notes",
            "material_type": "notes",
        },
        files={"file": ("notes.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 201


def test_upload_uses_authenticated_user_id(client, _setup, user_auth):
    user_id, headers = user_auth
    course_id = _make_course(client, headers)
    response = client.post(
        "/api/materials/upload",
        data={
            "course_id": course_id,
            "title": "Notes",
            "material_type": "notes",
        },
        files={"file": ("notes.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["uploaded_by"] == str(user_id)


def test_client_cannot_impersonate_uploader(client, _setup, user_auth):
    user_id, headers = user_auth
    other_id = str(uuid.uuid4())
    course_id = _make_course(client, headers)
    response = client.post(
        "/api/materials/upload",
        data={
            "course_id": course_id,
            "uploaded_by": other_id,
            "title": "Notes",
            "material_type": "notes",
        },
        files={"file": ("notes.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["uploaded_by"] == str(user_id)
    assert response.json()["uploaded_by"] != other_id


def test_unauthorized_material_deletion_returns_403(client, _setup):
    owner = make_db_user(name="Owner", email="owner@example.com")
    other = make_db_user(name="Other", email="other@example.com")
    owner_headers = auth_headers_for(owner)
    other_headers = auth_headers_for(other)

    course_id = _make_course(client, owner_headers)
    material_id = client.post(
        "/api/materials",
        json={
            "course_id": course_id,
            "title": "Notes",
            "material_type": "notes",
        },
        headers=owner_headers,
    ).json()["id"]

    assert (
        client.delete(f"/api/materials/{material_id}", headers=other_headers).status_code
        == 403
    )
    assert (
        client.delete(f"/api/materials/{material_id}", headers=owner_headers).status_code
        == 204
    )