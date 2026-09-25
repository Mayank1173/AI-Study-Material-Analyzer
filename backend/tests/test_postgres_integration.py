"""Live PostgreSQL integration tests.

These tests exercise the full API against a REAL PostgreSQL database. They are
strictly separate from the SQLite-backed unit tests in this directory so that
the unit-test suite keeps running with zero database setup.

Running them
------------

1. Create a dedicated test database (never a production database):

       createdb ai_study_material_analyzer_test

2. Run ONLY this file (or run the whole suite; every test here is skipped
   when no PostgreSQL URL is available):

       pytest tests/test_postgres_integration.py -v --tb=short

URL resolution
--------------

- If the TEST_DATABASE_URL environment variable is set, it is used as-is.
- Otherwise, the test URL is derived automatically from DATABASE_URL in
  ``backend/.env`` by changing only the database name to
  ``ai_study_material_analyzer_test`` (driver, user, password, host and port
  are preserved exactly).
- If neither is available, the module is skipped.

Guidelines
----------
- Credentials are never hard-coded in this file: the connection is read from
  TEST_DATABASE_URL or the project's DATABASE_URL, and the password is never
  printed.
- No destructive DROP DATABASE is ever executed. Each test only drops/recreates
  the tables inside the already-existing test database (Base.metadata.drop_all
  then create_all), which keeps every run independent without destroying the
  database itself.
"""
import os
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

# Dedicated test database name; the rest of the connection (driver, user,
# password, host, port) is taken verbatim from the project's DATABASE_URL.
TEST_DATABASE_NAME = "ai_study_material_analyzer_test"

# Load the project's backend/.env so DATABASE_URL can serve as the fallback
# when TEST_DATABASE_URL is not explicitly provided. load_dotenv does not
# override existing environment variables by default, so an explicitly set
# TEST_DATABASE_URL always takes priority.
_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_ENV_FILE)

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    _database_url = os.getenv("DATABASE_URL")
    if _database_url:
        # Derive the test URL by changing ONLY the database name. Parsing and
        # re-rendering with make_url preserves the exact user/password/host/
        # port (including any URL-encoded characters) instead of string-editing
        # the raw URL, which previously caused password authentication failures.
        _url = make_url(_database_url)
        _url = _url.set(database=TEST_DATABASE_NAME)
        TEST_DATABASE_URL = _url.render_as_string(hide_password=False)

if not TEST_DATABASE_URL:
    pytest.skip(
        "TEST_DATABASE_URL not set and no DATABASE_URL in backend/.env - "
        "skipping live PostgreSQL integration tests",
        allow_module_level=True,
    )

# The application also connects to a live database for /health/database and
# /health/ready. Point the app engine at the same integration database so
# those endpoints report real connectivity (DATABASE_URL may be exported to
# override this). get_settings() is lru-cached and the engine is a module
# global created at import time, so both are reset explicitly.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

import app.db.session as db_session  # noqa: E402

db_session.engine = None

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.core.security import (  # noqa: E402
    create_access_token,
    hash_password,
)
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models import StudyMaterial, User  # noqa: E402
from main import app  # noqa: E402

TEST_PASSWORD = "testpassword123"


@pytest.fixture(scope="module")
def pg_engine():
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture()
def client(pg_engine):
    """Fresh schema and TestClient against PostgreSQL for every test.

    Only the tables are reset (drop_all/create_all); the database itself is
    never dropped.
    """
    if TEST_DATABASE_URL.startswith("sqlite"):
        pytest.fail("TEST_DATABASE_URL must point at PostgreSQL for integration tests")

    Base.metadata.drop_all(bind=pg_engine)
    Base.metadata.create_all(bind=pg_engine)

    TestSession = sessionmaker(bind=pg_engine, expire_on_commit=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_user(
    db: Session, *, name: str, email: str, password: str = TEST_PASSWORD
) -> User:
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def _register_user(
    client, *, name="Integration User", email="pg-user@example.com"
) -> dict:
    """Register a new user via the public API."""
    response = client.post(
        "/api/auth/register",
        json={
            "name": name,
            "email": email,
            "password": TEST_PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _login(client, email: str, password: str = TEST_PASSWORD) -> str:
    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_postgres_connection_and_version(pg_engine):
    with pg_engine.connect() as connection:
        server_version = connection.execute(text("SELECT version()")).scalar()
    assert "PostgreSQL" in server_version


def test_full_user_material_workflow(client, pg_engine):
    """End-to-end: create users, upload materials, list/download/delete.

    Any authenticated user can create courses and upload materials to any
    course.  Materials are private to the user who uploaded them.
    """
    TestSession = sessionmaker(bind=pg_engine, expire_on_commit=False)

    session = TestSession()
    owner = _create_user(
        session, name="PG Owner", email="pg-owner@example.com"
    )
    session.close()

    other_me = _register_user(
        client, name="PG Other", email="pg-other@example.com"
    )
    other_id = other_me["id"]

    owner_token = _login(client, "pg-owner@example.com")
    other_token = _login(client, "pg-other@example.com")

    owner_headers = _auth_headers(owner)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    me_response = client.get("/api/auth/me", headers=owner_headers)
    assert me_response.status_code == 200
    assert me_response.json()["id"] == str(owner.id)

    other_me_response = client.get("/api/auth/me", headers=other_headers)
    assert other_me_response.status_code == 200
    assert other_me_response.json()["id"] == other_id

    course_response = client.post(
        "/api/courses",
        headers=owner_headers,
        json={
            "name": "PostgreSQL Integration",
            "code": "PG101",
            "description": "End-to-end subject",
        },
    )
    assert course_response.status_code == 201, course_response.text
    course = course_response.json()
    course_id = course["id"]

    view_response = client.get(
        f"/api/courses/{course_id}", headers=other_headers
    )
    assert view_response.status_code == 200
    assert view_response.json()["id"] == course_id

    upload_response = client.post(
        "/api/materials/upload",
        headers=other_headers,
        data={
            "course_id": course_id,
            "title": "Integration Notes",
            "material_type": "notes",
        },
        files={"file": ("integration-notes.txt", b"Hello PostgreSQL", "text/plain")},
    )
    assert upload_response.status_code == 201, upload_response.text
    material = upload_response.json()
    material_id = material["id"]
    assert material["file_name"] == "integration-notes.txt"
    assert material["status"] == "uploaded"
    assert material["uploaded_by"] == other_id

    session = TestSession()
    db_material = session.get(StudyMaterial, uuid.UUID(material_id))
    assert db_material is not None
    assert db_material.title == "Integration Notes"
    assert db_material.course_id == uuid.UUID(course_id)
    assert db_material.uploaded_by == uuid.UUID(other_id)
    db_material_id = db_material.id
    stored_name = db_material.stored_file_name
    session.close()

    if stored_name:
        stored_path = Path(get_settings().storage_dir) / stored_name
        assert stored_path.is_file(), f"stored file missing at {stored_path}"
        assert stored_path.read_bytes() == b"Hello PostgreSQL"

    other_list = client.get(
        f"/api/materials?course_id={course_id}", headers=other_headers
    )
    assert other_list.status_code == 200
    assert other_list.json()["total"] == 1

    other_view = client.get(
        f"/api/materials/{material_id}", headers=other_headers
    )
    assert other_view.status_code == 200

    owner_list = client.get(
        f"/api/materials?course_id={course_id}", headers=owner_headers
    )
    assert owner_list.status_code == 200
    assert owner_list.json()["total"] == 0

    owner_view = client.get(
        f"/api/materials/{material_id}", headers=owner_headers
    )
    assert owner_view.status_code == 403

    download = client.get(
        f"/api/materials/{material_id}/download", headers=other_headers
    )
    assert download.status_code == 200
    assert download.content == b"Hello PostgreSQL"

    delete_response = client.delete(
        f"/api/materials/{material_id}", headers=other_headers
    )
    assert delete_response.status_code == 204

    session = TestSession()
    assert session.get(StudyMaterial, db_material_id) is None
    session.close()
    if stored_name:
        assert not (Path(get_settings().storage_dir) / stored_name).is_file()


def test_postgres_health_endpoints(client):
    """Liveness is DB-independent; DB health/readiness reflect live PostgreSQL."""
    liveness = client.get("/health")
    assert liveness.status_code == 200
    assert liveness.json() == {"status": "healthy"}

    db_health = client.get("/health/database")
    assert db_health.status_code == 200
    assert db_health.json() == {"status": "healthy", "database": "connected"}

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "database": "connected"}


def test_database_error_and_edge_cases(client, pg_engine):
    """Edge cases against PostgreSQL: duplicates, cross-user access, uploads."""
    TestSession = sessionmaker(bind=pg_engine, expire_on_commit=False)

    session = TestSession()
    user_a = _create_user(
        session, name="PG User A", email="pg-user-a@example.com"
    )
    user_b = _create_user(
        session, name="PG User B", email="pg-user-b@example.com"
    )
    session.close()

    a_headers = _auth_headers(user_a)
    b_headers = _auth_headers(user_b)

    course_response = client.post(
        "/api/courses",
        headers=a_headers,
        json={"name": "Edge Course", "code": "PGEDGE", "description": None},
    )
    assert course_response.status_code == 201
    course_id = course_response.json()["id"]

    duplicate_course = client.post(
        "/api/courses",
        headers=a_headers,
        json={"name": "Edge Course Dupe", "code": "PGEDGE"},
    )
    assert duplicate_course.status_code == 409

    not_found_course = client.get(
        "/api/courses/00000000-0000-0000-0000-000000000000",
        headers=b_headers,
    )
    assert not_found_course.status_code == 404

    not_found_material = client.get(
        "/api/materials/00000000-0000-0000-0000-000000000000",
        headers=b_headers,
    )
    assert not_found_material.status_code == 404

    # User B can create a course with the same code (no global uniqueness)
    b_course = client.post(
        "/api/courses",
        headers=b_headers,
        json={"name": "B Course", "code": "PGEDGE"},
    )
    assert b_course.status_code == 201

    duplicate_email = client.post(
        "/api/auth/register",
        json={
            "name": "Clone",
            "email": "pg-user-a@example.com",
            "password": TEST_PASSWORD,
        },
    )
    assert duplicate_email.status_code == 409

    invalid_jwt = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert invalid_jwt.status_code == 401

    unauthenticated = client.get("/api/auth/me")
    assert unauthenticated.status_code == 401

    # Upload by user A to user A's course -> 201
    upload = client.post(
        "/api/materials/upload",
        headers=a_headers,
        data={
            "course_id": course_id,
            "title": "A File",
            "material_type": "notes",
        },
        files={"file": ("a.txt", b"a-content", "text/plain")},
    )
    assert upload.status_code == 201
    material_id = upload.json()["id"]

    # User B cannot view user A's material -> 403
    denied_get = client.get(
        f"/api/materials/{material_id}", headers=b_headers
    )
    assert denied_get.status_code == 403

    # User B listing a course they didn't upload to -> 200 empty (not 403)
    b_listing = client.get(
        f"/api/materials?course_id={course_id}", headers=b_headers
    )
    assert b_listing.status_code == 200
    assert b_listing.json()["total"] == 0

    # Unsupported file type -> 415
    bad_type = client.post(
        "/api/materials/upload",
        headers=a_headers,
        data={
            "course_id": course_id,
            "title": "Bad",
            "material_type": "notes",
        },
        files={"file": ("bad.exe", b"MZ", "application/octet-stream")},
    )
    assert bad_type.status_code == 415

    # Oversized file -> 413 (default MAX_UPLOAD_SIZE_MB is 20)
    oversized = client.post(
        "/api/materials/upload",
        headers=a_headers,
        data={
            "course_id": course_id,
            "title": "Huge",
            "material_type": "notes",
        },
        files={"file": ("big.txt", b"x" * (21 * 1024 * 1024), "text/plain")},
    )
    assert oversized.status_code == 413

    # Missing course -> 404
    missing_course = client.post(
        "/api/materials/upload",
        headers=a_headers,
        data={
            "course_id": "00000000-0000-0000-0000-000000000000",
            "title": "Missing",
            "material_type": "notes",
        },
        files={"file": ("m.txt", b"m", "text/plain")},
    )
    assert missing_course.status_code == 404

    # Owner deletes own material -> 204
    delete_response = client.delete(
        f"/api/materials/{material_id}", headers=a_headers
    )
    assert delete_response.status_code == 204