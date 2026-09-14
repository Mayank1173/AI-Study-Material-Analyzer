"""Live PostgreSQL integration tests.

These tests exercise the full API against a REAL PostgreSQL database. They are
strictly separate from the SQLite-backed unit tests in this directory so that
the unit-test suite keeps running with zero database setup.

Running them
------------

1. Create a dedicated test database (never a production database):

       createdb ai_study_material_analyzer_test

2. Point at it with the TEST_DATABASE_URL environment variable and run ONLY
   this file (or run the whole suite; every test here is skipped when the
   variable is absent):

       TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ai_study_material_analyzer_test \
       pytest tests/test_postgres_integration.py -v --tb=short

Guidelines
----------
- Credentials are never hard-coded in this file: the connection is read from
  the TEST_DATABASE_URL environment variable.
- No destructive DROP DATABASE is ever executed. Each test only drops/recreates
  the tables inside the already-existing test database (Base.metadata.drop_all
  then create_all), which keeps every run independent without destroying the
  database itself.
"""
import os
import uuid
from pathlib import Path

import pytest

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    pytest.skip(
        "TEST_DATABASE_URL not set - skipping live PostgreSQL integration tests",
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
    db: Session, *, name: str, email: str, role: str, password: str = TEST_PASSWORD
) -> User:
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.role)
    return {"Authorization": f"Bearer {token}"}


def _register_student(
    client, email: str = "pg-student@example.com"
) -> dict:
    """Public registration path always yields a student account."""
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Integration Student",
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


def test_full_teacher_student_material_workflow(client, pg_engine):
    """The complete teacher -> course -> enrollment -> upload -> download flow."""
    TestSession = sessionmaker(bind=pg_engine, expire_on_commit=False)

    session = TestSession()
    teacher = _create_user(
        session, name="PG Teacher", email="pg-teacher@example.com", role="teacher"
    )
    session.close()

    student_me = _register_student(client)
    student_id = student_me["id"]

    teacher_token = _login(client, "pg-teacher@example.com")
    student_token = _login(client, "pg-student@example.com")

    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    me_response = client.get("/api/auth/me", headers=teacher_headers)
    assert me_response.status_code == 200
    assert me_response.json()["role"] == "teacher"

    student_me_response = client.get("/api/auth/me", headers=student_headers)
    assert student_me_response.status_code == 200
    assert student_me_response.json()["id"] == student_id

    course_response = client.post(
        "/api/courses",
        headers=teacher_headers,
        json={
            "name": "PostgreSQL Integration",
            "code": "PG101",
            "description": "End-to-end course",
        },
    )
    assert course_response.status_code == 201, course_response.text
    course = course_response.json()
    course_id = course["id"]

    view_response = client.get(
        f"/api/courses/{course_id}", headers=student_headers
    )
    assert view_response.status_code == 200
    assert view_response.json()["id"] == course_id

    enroll_response = client.post(
        f"/api/courses/{course_id}/enroll", headers=student_headers
    )
    assert enroll_response.status_code == 201, enroll_response.text

    status_response = client.get(
        f"/api/courses/{course_id}/enrollments/me", headers=student_headers
    )
    assert status_response.status_code == 200
    assert status_response.json()["is_enrolled"] is True

    upload_response = client.post(
        "/api/materials/upload",
        headers=teacher_headers,
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

    session = TestSession()
    db_material = session.get(StudyMaterial, uuid.UUID(material_id))
    assert db_material is not None
    assert db_material.title == "Integration Notes"
    assert db_material.course_id == uuid.UUID(course_id)
    assert db_material.uploaded_by == teacher.id
    db_material_id = db_material.id
    session.close()

    stored_name = db_material.stored_file_name
    if stored_name:
        stored_path = Path(get_settings().storage_dir) / stored_name
        assert stored_path.is_file(), f"stored file missing at {stored_path}"
        assert stored_path.read_bytes() == b"Hello PostgreSQL"

    teacher_list = client.get(
        f"/api/materials?course_id={course_id}", headers=teacher_headers
    )
    assert teacher_list.status_code == 200
    assert teacher_list.json()["total"] == 1

    teacher_view = client.get(
        f"/api/materials/{material_id}", headers=teacher_headers
    )
    assert teacher_view.status_code == 200

    student_list = client.get(
        f"/api/materials?course_id={course_id}", headers=student_headers
    )
    assert student_list.status_code == 200
    assert student_list.json()["total"] == 1

    student_view = client.get(
        f"/api/materials/{material_id}", headers=student_headers
    )
    assert student_view.status_code == 200

    download = client.get(
        f"/api/materials/{material_id}/download", headers=student_headers
    )
    assert download.status_code == 200
    assert download.content == b"Hello PostgreSQL"

    # Cleanup: teacher deletes the material -> DB row and stored file removed.
    delete_response = client.delete(
        f"/api/materials/{material_id}", headers=teacher_headers
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
    """Duplicate/constraint/authorization edge cases against PostgreSQL."""
    TestSession = sessionmaker(bind=pg_engine, expire_on_commit=False)

    session = TestSession()
    teacher = _create_user(
        session, name="PG Teacher 2", email="pg-teacher2@example.com", role="teacher"
    )
    owner_teacher = _create_user(
        session,
        name="PG Owner",
        email="pg-owner@example.com",
        role="teacher",
    )
    session.close()

    teacher_headers = _auth_headers(teacher)
    owner_headers = _auth_headers(owner_teacher)

    _register_student(client)
    student_token = _login(client, "pg-student@example.com")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    course_response = client.post(
        "/api/courses",
        headers=owner_headers,
        json={"name": "Edge Course", "code": "PGEDGE", "description": None},
    )
    assert course_response.status_code == 201
    course_id = course_response.json()["id"]

    duplicate_course = client.post(
        "/api/courses",
        headers=owner_headers,
        json={"name": "Edge Course Dupe", "code": "PGEDGE"},
    )
    assert duplicate_course.status_code == 409

    not_found_course = client.get(
        "/api/courses/00000000-0000-0000-0000-000000000000",
        headers=student_headers,
    )
    assert not_found_course.status_code == 404

    not_found_material = client.get(
        "/api/materials/00000000-0000-0000-0000-000000000000",
        headers=student_headers,
    )
    assert not_found_material.status_code == 404

    assert client.post(
        "/api/courses", headers=owner_headers, json={"name": "No", "code": "XXX"}
    ).status_code == 201
    duplicate_email = client.post(
        "/api/auth/register",
        json={
            "name": "Clone",
            "email": "pg-student@example.com",
            "password": TEST_PASSWORD,
        },
    )
    assert duplicate_email.status_code == 409

    enroll = client.post(
        f"/api/courses/{course_id}/enroll", headers=student_headers
    )
    assert enroll.status_code == 201
    duplicate_enroll = client.post(
        f"/api/courses/{course_id}/enroll", headers=student_headers
    )
    assert duplicate_enroll.status_code == 409

    invalid_jwt = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert invalid_jwt.status_code == 401

    unauthenticated = client.get("/api/auth/me")
    assert unauthenticated.status_code == 401

    unscoped_teacher = client.post(
        "/api/courses",
        headers=teacher_headers,
        json={"name": "Other Teacher Course", "code": "OTHER1"},
    )
    assert unscoped_teacher.status_code == 201

    forbidden_upload = client.post(
        "/api/materials/upload",
        headers=teacher_headers,
        data={
            "course_id": course_id,
            "title": "Not Mine",
            "material_type": "notes",
        },
        files={"file": ("nope.txt", b"nope", "text/plain")},
    )
    assert forbidden_upload.status_code == 403

    material_upload = client.post(
        "/api/materials/upload",
        headers=owner_headers,
        data={
            "course_id": course_id,
            "title": "Owner File",
            "material_type": "notes",
        },
        files={"file": ("owner.txt", b"owner-content", "text/plain")},
    )
    assert material_upload.status_code == 201
    material_id = material_upload.json()["id"]

    other_student = _register_student(client, email="pg-other-student@example.com")
    other_token = _login(client, other_student["email"])
    other_headers = {"Authorization": f"Bearer {other_token}"}

    denied_other_student = client.get(
        f"/api/materials/{material_id}", headers=other_headers
    )
    assert denied_other_student.status_code == 403

    denied_listing = client.get(
        f"/api/materials?course_id={course_id}", headers=other_headers
    )
    assert denied_listing.status_code == 403

    owner_delete = client.delete(
        f"/api/materials/{material_id}", headers=owner_headers
    )
    assert owner_delete.status_code == 204