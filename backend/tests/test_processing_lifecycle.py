"""Material processing-lifecycle tests.

Processing itself is not implemented; these tests cover the data/API contract
a future processing worker and the frontend rely on: status transitions,
processing timestamps, failure messages, and pending-material discovery.
"""
import uuid

import pytest
from sqlalchemy import select

from app.models import Course, StudyMaterial, User
from app.schemas.course import CourseCreate
from app.services import course_service, study_material_service
from tests.conftest import auth_headers_for, make_db_user


def _course_for_teacher(client, headers, code="CS301"):
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


def _material_row(db, material_id):
    return db.get(StudyMaterial, uuid.UUID(material_id))


# ---------------- Default metadata ----------------


def test_created_material_has_empty_processing_fields(client, teacher_auth):
    _, headers = teacher_auth
    course_id = _course_for_teacher(client, headers)
    body = _create_material(client, headers, course_id)
    assert body["status"] == "uploaded"
    assert body["processed_at"] is None
    assert body["error_message"] is None


# ---------------- POST /api/materials/{id}/process ----------------


def test_teacher_can_start_processing(client, teacher_auth, db):
    _, headers = teacher_auth
    course_id = _course_for_teacher(client, headers)
    material_id = _create_material(client, headers, course_id)["id"]

    response = client.post(
        f"/api/materials/{material_id}/process", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processing"
    assert body["processed_at"] is None
    assert body["error_message"] is None
    assert _material_row(db, material_id).status == "processing"


def test_teacher_can_retry_failed_material(client, teacher_auth, db):
    _, headers = teacher_auth
    course_id = _course_for_teacher(client, headers)
    material_id = _create_material(client, headers, course_id)["id"]

    row = _material_row(db, material_id)
    row.status = "failed"
    row.error_message = "The file could not be parsed"
    db.commit()

    response = client.post(
        f"/api/materials/{material_id}/process", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processing"
    assert body["error_message"] is None


def test_cannot_process_material_already_processed(client, teacher_auth, db):
    _, headers = teacher_auth
    course_id = _course_for_teacher(client, headers)
    material_id = _create_material(client, headers, course_id)["id"]
    _material_row(db, material_id).status = "processed"
    db.commit()

    response = client.post(
        f"/api/materials/{material_id}/process", headers=headers
    )
    assert response.status_code == 409


def test_non_owner_teacher_cannot_process(client):
    owner = make_db_user(name="Owner", email="owner@example.com", role="teacher")
    other = make_db_user(name="Other", email="other@example.com", role="teacher")
    owner_headers = auth_headers_for(owner)
    other_headers = auth_headers_for(other)

    course_id = _course_for_teacher(client, owner_headers)
    material_id = _create_material(client, owner_headers, course_id)["id"]

    response = client.post(
        f"/api/materials/{material_id}/process", headers=other_headers
    )
    assert response.status_code == 403


def test_student_cannot_process(client, teacher_auth, student_auth):
    _, teacher_headers = teacher_auth
    _, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)
    material_id = _create_material(client, teacher_headers, course_id)["id"]

    response = client.post(
        f"/api/materials/{material_id}/process", headers=student_headers
    )
    assert response.status_code == 403


def test_process_missing_material_returns_404(client, teacher_auth):
    _, headers = teacher_auth
    response = client.post(
        f"/api/materials/{uuid.uuid4()}/process", headers=headers
    )
    assert response.status_code == 404


def test_process_requires_authentication(client, teacher_auth):
    _, headers = teacher_auth
    course_id = _course_for_teacher(client, headers)
    material_id = _create_material(client, headers, course_id)["id"]
    assert (
        client.post(f"/api/materials/{material_id}/process").status_code == 401
    )


# ---------------- Status filter validation ----------------


def test_invalid_status_filter_rejected(client, teacher_auth):
    _, headers = teacher_auth
    response = client.get("/api/materials?status=bogus", headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_valid_status_filters_accepted(client, teacher_auth):
    _, headers = teacher_auth
    for status in ("uploaded", "processing", "processed", "failed"):
        response = client.get(
            f"/api/materials?status={status}", headers=headers
        )
        assert response.status_code == 200


# ---------------- Service-layer worker contract ----------------


def _seed_material(db_session, *, status="uploaded", error_message=None):
    """Create a minimal teacher -> course -> material chain for service tests."""
    teacher = User(
        name="Prof. Contract",
        email=f"contract_{uuid.uuid4().hex[:8]}@example.com",
        role="teacher",
    )
    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)

    course = course_service.create_course(
        db_session,
        CourseCreate(
            name="Contract Course", code=f"CT{uuid.uuid4().hex[:6]}"
        ),
        teacher_id=teacher.id,
    )

    material = StudyMaterial(
        course_id=course.id,
        uploaded_by=teacher.id,
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


def test_response_exposes_failure_information(client, teacher_auth, db):
    _, headers = teacher_auth
    course_id = _course_for_teacher(client, headers)
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


def test_pending_material_visible_via_status_filter(client, teacher_auth, db):
    _, headers = teacher_auth
    course_id = _course_for_teacher(client, headers)
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
