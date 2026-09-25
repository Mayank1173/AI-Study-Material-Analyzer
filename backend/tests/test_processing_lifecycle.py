"""Material processing-lifecycle tests.

Tests cover the data/API contract for status transitions, processing
timestamps, failure messages, pending-material discovery, and the real
integration between backend processing and the RAG knowledge base.
"""
import uuid
from io import BytesIO

import pytest
from sqlalchemy import select

from app.models import Course, StudyMaterial, User
from app.schemas.course import CourseCreate
from app.services import course_service, study_material_service
from tests.conftest import make_db_user


def _create_course(client, headers, code="CS301"):
    response = client.post(
        "/api/courses",
        json={"name": "Databases", "code": code},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_material(client, headers, course_id, title="Notes"):
    response = client.post(
        "/api/materials",
        json={
            "course_id": course_id,
            "title": title,
            "material_type": "notes",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _upload_material(client, headers, course_id, filename="notes.txt", content=b"Hello world", title="Uploaded Notes"):
    data = {
        "course_id": course_id,
        "title": title,
        "material_type": "notes",
    }
    files = {"file": (filename, BytesIO(content), "text/plain")}
    response = client.post("/api/materials/upload", data=data, files=files, headers=headers)
    assert response.status_code == 201
    return response.json()


def _material_row(db, material_id):
    return db.get(StudyMaterial, uuid.UUID(material_id))


# ---------------- Default metadata ----------------


def test_created_material_has_empty_processing_fields(client, user_auth):
    _, headers = user_auth
    course_id = _create_course(client, headers)
    body = _create_material(client, headers, course_id)
    assert body["status"] == "uploaded"
    assert body["processed_at"] is None
    assert body["error_message"] is None


# ---------------- POST /api/materials/{id}/process (no stored file) ----------------


def test_process_material_without_stored_file_fails(client, user_auth, db):
    """A material created via the JSON endpoint has no stored file and fails."""
    _, headers = user_auth
    course_id = _create_course(client, headers)
    material_id = _create_material(client, headers, course_id)["id"]

    response = client.post(
        f"/api/materials/{material_id}/process", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert "no stored file" in body["error_message"].lower()


# ---------------- Real file processing ----------------


def test_owner_can_upload_and_process(client, user_auth, db, tmp_path, monkeypatch):
    """Upload a real TXT file and process it into the RAG knowledge base."""
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    from app.core.config import get_settings
    get_settings.cache_clear()

    _, headers = user_auth
    course_id = _create_course(client, headers)
    body = _upload_material(
        client, headers, course_id,
        filename="notes.txt",
        content=b"Photosynthesis converts light energy into chemical energy.",
        title="Biology Notes",
    )
    assert body["status"] == "uploaded"

    response = client.post(
        f"/api/materials/{body['id']}/process", headers=headers
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "processed"
    assert result["processed_at"] is not None
    assert result["error_message"] is None
    get_settings.cache_clear()


def test_retry_failed_material_succeeds(client, user_auth, db, tmp_path, monkeypatch):
    """A failed material can be retried and succeeds on second attempt."""
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    from app.core.config import get_settings
    get_settings.cache_clear()

    _, headers = user_auth
    course_id = _create_course(client, headers)
    body = _upload_material(client, headers, course_id, filename="notes.txt", content=b"Test content")

    # Simulate failure by setting status to failed
    row = _material_row(db, body["id"])
    row.status = "failed"
    row.error_message = "Previous error"
    db.commit()

    response = client.post(
        f"/api/materials/{body['id']}/process", headers=headers
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "processed"
    assert result["error_message"] is None
    get_settings.cache_clear()


# ---------------- Invalid transitions remain protected ----------------


def test_cannot_process_material_already_processed(client, user_auth, db):
    _, headers = user_auth
    course_id = _create_course(client, headers)
    material_id = _create_material(client, headers, course_id)["id"]
    _material_row(db, material_id).status = "processed"
    db.commit()

    response = client.post(
        f"/api/materials/{material_id}/process", headers=headers
    )
    assert response.status_code == 409


def test_another_user_cannot_process_material(client, user_auth, second_user_auth, db):
    _, headers = user_auth
    _, other_headers = second_user_auth
    course_id = _create_course(client, headers)
    material_id = _create_material(client, headers, course_id)["id"]

    response = client.post(
        f"/api/materials/{material_id}/process", headers=other_headers
    )
    assert response.status_code == 403


def test_process_missing_material_returns_404(client, user_auth):
    _, headers = user_auth
    response = client.post(
        f"/api/materials/{uuid.uuid4()}/process", headers=headers
    )
    assert response.status_code == 404


def test_process_requires_authentication(client, user_auth):
    _, headers = user_auth
    course_id = _create_course(client, headers)
    material_id = _create_material(client, headers, course_id)["id"]
    assert (
        client.post(f"/api/materials/{material_id}/process").status_code == 401
    )


# ---------------- Unsupported file types ----------------


def test_unsupported_format_rejected_at_upload(client, user_auth):
    """Images such as .png are rejected at upload time (415), not stored."""
    _, headers = user_auth
    course_id = _create_course(client, headers)
    response = client.post(
        "/api/materials/upload",
        data={
            "course_id": course_id,
            "title": "Diagram",
            "material_type": "notes",
        },
        files={"file": ("diagram.png", b"\x89PNG fake bytes", "image/png")},
        headers=headers,
    )
    assert response.status_code == 415


def test_corrupt_pdf_processing_fails(client, user_auth, db, tmp_path, monkeypatch):
    """A file with an allowed extension that cannot be parsed results in failed."""
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    from app.core.config import get_settings
    get_settings.cache_clear()

    _, headers = user_auth
    course_id = _create_course(client, headers)
    body = _upload_material(
        client,
        headers,
        course_id,
        filename="broken.pdf",
        content=b"%PDF-1.4 this is not a real pdf",
        title="Broken Notes",
    )
    assert body["status"] == "uploaded"

    response = client.post(
        f"/api/materials/{body['id']}/process", headers=headers
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "failed"
    assert result["error_message"]
    get_settings.cache_clear()


# ---------------- URL material processing ----------------


def test_url_material_processing_fails(client, user_auth, db):
    """A URL-only material has no stored file and fails processing."""
    _, headers = user_auth
    course_id = _create_course(client, headers)
    response = client.post(
        "/api/materials/upload",
        data={
            "course_id": course_id,
            "title": "Web Notes",
            "material_type": "notes",
            "source_url": "https://example.com/notes.pdf",
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()

    response = client.post(
        f"/api/materials/{body['id']}/process", headers=headers
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "failed"
    assert "no stored file" in result["error_message"].lower()


# ---------------- Status filter validation ----------------


def test_invalid_status_filter_rejected(client, user_auth):
    _, headers = user_auth
    response = client.get("/api/materials?status=bogus", headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_valid_status_filters_accepted(client, user_auth):
    _, headers = user_auth
    for status in ("uploaded", "processing", "processed", "failed"):
        response = client.get(
            f"/api/materials?status={status}", headers=headers
        )
        assert response.status_code == 200


# ---------------- Service-layer worker contract ----------------


def _seed_material(db_session, *, status="uploaded", error_message=None):
    """Create a minimal user -> course -> material chain for service tests."""
    user = User(
        name="Contract User",
        email=f"contract_{uuid.uuid4().hex[:8]}@example.com",
        role="student",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    course = course_service.create_course(
        db_session,
        CourseCreate(
            name="Contract Course", code=f"CT{uuid.uuid4().hex[:6]}"
        ),
        owner_id=user.id,
    )

    material = StudyMaterial(
        course_id=course.id,
        uploaded_by=user.id,
        title="Contract Notes",
        material_type="notes",
        status=status,
        error_message=error_message,
    )
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)
    return material


def test_service_lists_only_uploaded_materials_pending(db_session):
    pending = _seed_material(db_session, status="uploaded")
    _seed_material(db_session, status="processed")
    _seed_material(db_session, status="failed")

    result = study_material_service.list_materials_pending_processing(db_session)
    ids = {m.id for m in result}
    assert pending.id in ids
    assert len(result) == 1


def test_service_mark_processing_clears_old_failure(db_session):
    material = _seed_material(db_session, status="failed", error_message="boom")
    result = study_material_service.mark_material_processing(
        db_session, material.id
    )
    assert result.status == "processing"
    assert result.processed_at is None
    assert result.error_message is None


def test_service_mark_processed_sets_timestamp(db_session):
    material = _seed_material(db_session, status="processing")
    result = study_material_service.mark_material_processed(
        db_session, material.id
    )
    assert result.status == "processed"
    assert result.processed_at is not None
    assert result.error_message is None


def test_service_mark_failed_sets_message_and_no_timestamp(db_session):
    material = _seed_material(db_session, status="processing")
    result = study_material_service.mark_material_failed(
        db_session, material.id, error_message="Could not read the document"
    )
    assert result.status == "failed"
    assert result.error_message == "Could not read the document"
    assert result.processed_at is None


def test_service_failure_message_truncated(db_session):
    material = _seed_material(db_session, status="processing")
    long_message = "x" * 5000
    result = study_material_service.mark_material_failed(
        db_session, material.id, error_message=long_message
    )
    assert result.error_message == "x" * 1000


# ---------------- Response exposes processing fields ----------------


def test_response_exposes_failure_information(client, user_auth, db):
    _, headers = user_auth
    course_id = _create_course(client, headers)
    material_id = _create_material(client, headers, course_id)["id"]
    _material_row(db, material_id).status = "failed"
    db.commit()

    response = client.get(f"/api/materials/{material_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert "processed_at" in body
    assert "error_message" in body
    assert body["error_message"] is None


def test_pending_material_visible_via_status_filter(client, user_auth, db):
    _, headers = user_auth
    course_id = _create_course(client, headers)
    material_id = _create_material(client, headers, course_id)["id"]
    _material_row(db, material_id).status = "processing"
    db.commit()

    response = client.get(
        f"/api/materials?course_id={course_id}&status=processing",
        headers=headers,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == material_id
