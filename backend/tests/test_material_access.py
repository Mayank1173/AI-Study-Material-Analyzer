import uuid

import pytest

from app.core.config import get_settings
from app.models import StudyMaterial
from tests.conftest import auth_headers_for, make_db_user


@pytest.fixture()
def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _course_for_teacher(client, teacher_headers, code="CS301"):
    response = client.post(
        "/api/courses",
        json={"name": "Databases", "code": code},
        headers=teacher_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _upload(client, headers, course_id, **overrides):
    data = {"course_id": course_id, "title": "Notes", "material_type": "notes"}
    data.update(overrides)
    return client.post(
        "/api/materials/upload",
        data=data,
        files={"file": ("notes.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=headers,
    )


def _enroll(client, course_id, student_headers):
    return client.post(f"/api/courses/{course_id}/enroll", headers=student_headers)


# ---------------- Upload ----------------


def test_course_owner_can_upload_material(client, _setup, teacher_auth):
    _, headers = teacher_auth
    course_id = _course_for_teacher(client, headers)
    response = _upload(client, headers, course_id)
    assert response.status_code == 201


def test_non_owner_teacher_cannot_upload_material(client, _setup):
    owner = make_db_user(name="Owner", email="owner@example.com", role="teacher")
    other = make_db_user(name="Other", email="other@example.com", role="teacher")
    owner_headers = auth_headers_for(owner)
    other_headers = auth_headers_for(other)

    course_id = _course_for_teacher(client, owner_headers)
    response = _upload(client, other_headers, course_id)
    assert response.status_code == 403


def test_student_cannot_upload_material(client, _setup, teacher_auth, student_auth):
    _, teacher_headers = teacher_auth
    _, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)
    response = _upload(client, student_headers, course_id)
    assert response.status_code == 403


# ---------------- Read / list ----------------


def test_owner_can_get_material_metadata(client, _setup, teacher_auth):
    _, headers = teacher_auth
    course_id = _course_for_teacher(client, headers)
    material_id = _upload(client, headers, course_id).json()["id"]
    response = client.get(f"/api/materials/{material_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == material_id


def test_enrolled_student_can_get_material(client, _setup, teacher_auth, student_auth):
    _, teacher_headers = teacher_auth
    _, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)
    material_id = _upload(client, teacher_headers, course_id).json()["id"]

    assert _enroll(client, course_id, student_headers).status_code == 201
    response = client.get(f"/api/materials/{material_id}", headers=student_headers)
    assert response.status_code == 200


def test_non_enrolled_student_cannot_get_material(
    client, _setup, teacher_auth, student_auth
):
    _, teacher_headers = teacher_auth
    _, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)
    material_id = _upload(client, teacher_headers, course_id).json()["id"]

    response = client.get(f"/api/materials/{material_id}", headers=student_headers)
    assert response.status_code == 403


def test_non_owner_teacher_cannot_get_material(client, _setup):
    owner = make_db_user(name="Owner", email="owner@example.com", role="teacher")
    other = make_db_user(name="Other", email="other@example.com", role="teacher")
    owner_headers = auth_headers_for(owner)
    other_headers = auth_headers_for(other)

    course_id = _course_for_teacher(client, owner_headers)
    material_id = _upload(client, owner_headers, course_id).json()["id"]
    response = client.get(f"/api/materials/{material_id}", headers=other_headers)
    assert response.status_code == 403


def test_student_list_only_sees_enrolled_courses(client, _setup, teacher_auth):
    _, teacher_headers = teacher_auth
    viewer = make_db_user(name="Viewer", email="viewer@example.com", role="student")
    viewer_headers = auth_headers_for(viewer)

    course_id = _course_for_teacher(client, teacher_headers)
    _upload(client, teacher_headers, course_id)

    response = client.get("/api/materials", headers=viewer_headers)
    assert response.status_code == 200
    assert response.json()["items"] == []

    assert _enroll(client, course_id, viewer_headers).status_code == 201
    response = client.get("/api/materials", headers=viewer_headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_student_cannot_list_course_materials_of_unenrolled_course(
    client, _setup, teacher_auth, student_auth
):
    _, teacher_headers = teacher_auth
    _, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)
    _upload(client, teacher_headers, course_id)

    response = client.get(
        f"/api/materials?course_id={course_id}", headers=student_headers
    )
    assert response.status_code == 403


def test_list_materials_by_course_id_requires_access(client, _setup, teacher_auth):
    _, teacher_headers = teacher_auth
    course_id = _course_for_teacher(client, teacher_headers)
    _upload(client, teacher_headers, course_id)

    owner = make_db_user(
        name="Second Teacher", email="second@example.com", role="teacher"
    )
    response = client.get(
        f"/api/materials?course_id={course_id}",
        headers=auth_headers_for(owner),
    )
    assert response.status_code == 403


# ---------------- Download ----------------


def test_enrolled_student_can_download_material(
    client, _setup, teacher_auth, student_auth, db
):
    _, teacher_headers = teacher_auth
    _, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)
    material = _upload(client, teacher_headers, course_id).json()

    stored_name = db.get(StudyMaterial, uuid.UUID(material["id"])).stored_file_name
    stored_path = get_settings().storage_dir / stored_name
    expected = stored_path.read_bytes()

    assert _enroll(client, course_id, student_headers).status_code == 201
    response = client.get(
        f"/api/materials/{material['id']}/download", headers=student_headers
    )
    assert response.status_code == 200
    assert response.content == expected


def test_non_enrolled_student_cannot_download_material(
    client, _setup, teacher_auth, student_auth
):
    _, teacher_headers = teacher_auth
    _, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)
    material_id = _upload(client, teacher_headers, course_id).json()["id"]

    response = client.get(
        f"/api/materials/{material_id}/download", headers=student_headers
    )
    assert response.status_code == 403


def test_non_owner_teacher_cannot_download_material(client, _setup):
    owner = make_db_user(name="Owner", email="owner@example.com", role="teacher")
    other = make_db_user(name="Other", email="other@example.com", role="teacher")
    owner_headers = auth_headers_for(owner)
    other_headers = auth_headers_for(other)

    course_id = _course_for_teacher(client, owner_headers)
    material_id = _upload(client, owner_headers, course_id).json()["id"]
    response = client.get(
        f"/api/materials/{material_id}/download", headers=other_headers
    )
    assert response.status_code == 403


# ---------------- Delete ----------------


def test_course_owner_can_delete_material(client, _setup, teacher_auth, db):
    _, headers = teacher_auth
    course_id = _course_for_teacher(client, headers)
    material = _upload(client, headers, course_id).json()

    stored_file = get_settings().storage_dir / db.get(
        StudyMaterial, uuid.UUID(material["id"])
    ).stored_file_name
    assert stored_file.is_file()

    response = client.delete(f"/api/materials/{material['id']}", headers=headers)
    assert response.status_code == 204
    assert not stored_file.exists()


def test_non_owner_teacher_cannot_delete_material(client, _setup):
    owner = make_db_user(name="Owner", email="owner@example.com", role="teacher")
    other = make_db_user(name="Other", email="other@example.com", role="teacher")
    owner_headers = auth_headers_for(owner)
    other_headers = auth_headers_for(other)

    course_id = _course_for_teacher(client, owner_headers)
    material_id = _upload(client, owner_headers, course_id).json()["id"]

    response = client.delete(f"/api/materials/{material_id}", headers=other_headers)
    assert response.status_code == 403


def test_enrolled_student_cannot_delete_material(
    client, _setup, teacher_auth, student_auth
):
    _, teacher_headers = teacher_auth
    _, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)
    material_id = _upload(client, teacher_headers, course_id).json()["id"]

    assert _enroll(client, course_id, student_headers).status_code == 201
    response = client.delete(f"/api/materials/{material_id}", headers=student_headers)
    assert response.status_code == 403


# ---------------- Authentication ----------------


def test_unauthenticated_access_returns_401(client, _setup, teacher_auth):
    _, headers = teacher_auth
    course_id = _course_for_teacher(client, headers)
    material_id = _upload(client, headers, course_id).json()["id"]

    assert client.get(f"/api/materials/{material_id}").status_code == 401
    assert (
        client.get(f"/api/materials/{material_id}/download").status_code == 401
    )
    assert client.delete(f"/api/materials/{material_id}").status_code == 401


def test_upload_ownership_check_is_reusable_via_service(client, _setup):
    owner = make_db_user(name="Owner", email="owner@example.com", role="teacher")
    other = make_db_user(name="Other", email="other@example.com", role="teacher")
    owner_headers = auth_headers_for(owner)
    other_headers = auth_headers_for(other)

    course_id = _course_for_teacher(client, owner_headers)
    assert (
        client.post(
            "/api/materials",
            json={
                "course_id": course_id,
                "title": "Notes",
                "material_type": "notes",
            },
            headers=other_headers,
        ).status_code
        == 403
    )