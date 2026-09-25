"""Material ownership tests.

Materials are private to the user who uploaded them. Any authenticated user
may upload to any existing course. Only the uploader may view, list, download,
or delete a given material.
"""

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


def _create_course(client, headers, name="Databases", code="CS301"):
    response = client.post(
        "/api/courses",
        json={"name": name, "code": code},
        headers=headers,
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


# ---------------- Upload ----------------


def test_user_can_upload_material(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _create_course(client, headers)
    response = _upload(client, headers, course_id)
    assert response.status_code == 201


def test_second_user_can_upload_to_course_created_by_others(
    client, _setup, second_user_auth
):
    """Any authenticated user can upload to any existing course."""
    _, other_headers = second_user_auth
    course_id = _create_course(client, other_headers)

    third_user = make_db_user(name="Third", email="third@example.com")
    third_headers = auth_headers_for(third_user)
    response = _upload(client, third_headers, course_id)
    assert response.status_code == 201
    assert response.json()["uploaded_by"] == str(third_user.id)


# ---------------- Read / list ----------------


def test_owner_can_get_material_metadata(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _create_course(client, headers)
    material_id = _upload(client, headers, course_id).json()["id"]
    response = client.get(f"/api/materials/{material_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == material_id


def test_other_user_cannot_get_material(client, _setup, user_auth, second_user_auth):
    _, headers = user_auth
    _, other_headers = second_user_auth
    course_id = _create_course(client, headers)
    material_id = _upload(client, headers, course_id).json()["id"]

    response = client.get(f"/api/materials/{material_id}", headers=other_headers)
    assert response.status_code == 403


def test_list_only_shows_own_materials(client, _setup, user_auth, second_user_auth):
    _, headers = user_auth
    _, other_headers = second_user_auth
    course_id = _create_course(client, headers)
    _upload(client, headers, course_id)

    response = client.get("/api/materials", headers=other_headers)
    assert response.status_code == 200
    assert response.json()["items"] == []

    response = client.get("/api/materials", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_list_by_course_id_scoped_to_uploader(client, _setup, user_auth, second_user_auth):
    _, headers = user_auth
    _, other_headers = second_user_auth
    course_id = _create_course(client, headers)
    _upload(client, headers, course_id)

    # The other user uploaded nothing to this course — list returns empty (not
    # 403), because the course exists and the query is valid.
    response = client.get(
        f"/api/materials?course_id={course_id}", headers=other_headers
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_list_by_course_id_nonexistent_returns_404(client, _setup, user_auth):
    _, headers = user_auth
    response = client.get(
        f"/api/materials?course_id={uuid.uuid4()}", headers=headers
    )
    assert response.status_code == 404


# ---------------- Download ----------------


def test_owner_can_download_material(client, _setup, user_auth, db):
    _, headers = user_auth
    course_id = _create_course(client, headers)
    material = _upload(client, headers, course_id).json()

    stored_name = db.get(StudyMaterial, uuid.UUID(material["id"])).stored_file_name
    stored_path = get_settings().storage_dir / stored_name
    expected = stored_path.read_bytes()

    response = client.get(
        f"/api/materials/{material['id']}/download", headers=headers
    )
    assert response.status_code == 200
    assert response.content == expected


def test_other_user_cannot_download_material(
    client, _setup, user_auth, second_user_auth
):
    _, headers = user_auth
    _, other_headers = second_user_auth
    course_id = _create_course(client, headers)
    material_id = _upload(client, headers, course_id).json()["id"]

    response = client.get(
        f"/api/materials/{material_id}/download", headers=other_headers
    )
    assert response.status_code == 403


# ---------------- Delete ----------------


def test_owner_can_delete_material(client, _setup, user_auth, db):
    _, headers = user_auth
    course_id = _create_course(client, headers)
    material = _upload(client, headers, course_id).json()

    stored_file = get_settings().storage_dir / db.get(
        StudyMaterial, uuid.UUID(material["id"])
    ).stored_file_name
    assert stored_file.is_file()

    response = client.delete(f"/api/materials/{material['id']}", headers=headers)
    assert response.status_code == 204
    assert not stored_file.exists()


def test_other_user_cannot_delete_material(client, _setup, user_auth, second_user_auth):
    _, headers = user_auth
    _, other_headers = second_user_auth
    course_id = _create_course(client, headers)
    material_id = _upload(client, headers, course_id).json()["id"]

    response = client.delete(f"/api/materials/{material_id}", headers=other_headers)
    assert response.status_code == 403


# ---------------- Authentication ----------------


def test_unauthenticated_access_returns_401(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _create_course(client, headers)
    material_id = _upload(client, headers, course_id).json()["id"]

    assert client.get(f"/api/materials/{material_id}").status_code == 401
    assert client.get(f"/api/materials/{material_id}/download").status_code == 401
    assert client.delete(f"/api/materials/{material_id}").status_code == 401


# ---------------- Service-level ownership ----------------


def test_assert_owns_material_rejects_other_users(client, _setup, db):
    from app.services import study_material_service
    from app.services.errors import AccessDeniedError

    owner = make_db_user(name="Owner", email="owner@example.com")
    other = make_db_user(name="Other", email="other@example.com")

    course_id = _create_course(client, auth_headers_for(owner))
    material = client.post(
        "/api/materials",
        json={
            "course_id": course_id,
            "title": "Notes",
            "material_type": "notes",
        },
        headers=auth_headers_for(owner),
    ).json()

    material_obj = db.get(StudyMaterial, uuid.UUID(material["id"]))

    with pytest.raises(AccessDeniedError):
        study_material_service.assert_owns_material(other, material_obj)
