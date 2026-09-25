import uuid
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.models import StudyMaterial


def _stored_name(db, material_id):
    material = db.get(StudyMaterial, material_id)
    assert material is not None
    return material.stored_file_name


@pytest.fixture()
def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _make_user_and_course(client, headers):
    course_id = client.post(
        "/api/courses", json={"name": "Databases", "code": "CS301"}, headers=headers
    ).json()["id"]
    return course_id


def _upload(client, headers, course_id, filename, content, content_type, **overrides):
    data = {
        "course_id": course_id,
        "title": "Chapter 1 Notes",
        "material_type": "notes",
    }
    data.update(overrides)
    files = (
        {"file": (filename, content, content_type)}
        if filename is not None
        else None
    )
    return client.post("/api/materials/upload", data=data, files=files, headers=headers)


def test_upload_valid_pdf(client, _setup, db, user_auth):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    content = b"%PDF-1.4 fake pdf content"
    response = _upload(
        client, headers, course_id, "notes.pdf", content, "application/pdf"
    )
    assert response.status_code == 201
    body = response.json()
    assert body["file_name"] == "notes.pdf"
    assert body["file_size"] == len(content)
    assert body["mime_type"] == "application/pdf"
    assert body["status"] == "uploaded"
    assert body["source_url"] is None

    stored = _stored_name(db, uuid.UUID(body["id"]))
    assert stored == f"{body['id']}.pdf"
    assert (Path(get_settings().storage_dir) / stored).is_file()


def test_upload_valid_docx(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    content = b"PK\x03\x04 fake docx content"
    response = _upload(
        client,
        headers,
        course_id,
        "report.docx",
        content,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert response.status_code == 201
    assert response.json()["mime_type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml"
    )


def test_upload_valid_pptx(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    content = b"PK\x03\x04 fake pptx content"
    response = _upload(
        client,
        headers,
        course_id,
        "slides.pptx",
        content,
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    assert response.status_code == 201
    assert response.json()["mime_type"].startswith(
        "application/vnd.openxmlformats-officedocument.presentationml"
    )


def test_upload_valid_txt(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    content = b"Hello world"
    response = _upload(client, headers, course_id, "notes.txt", content, "text/plain")
    assert response.status_code == 201
    body = response.json()
    assert body["file_name"] == "notes.txt"
    assert body["mime_type"] == "text/plain"


REJECTED_EXTENSIONS = [
    ("legacy.ppt", "application/vnd.ms-powerpoint"),
    ("legacy.doc", "application/msword"),
    ("diagram.png", "image/png"),
    ("picture.jpg", "image/jpeg"),
    ("picture.jpeg", "image/jpeg"),
]


@pytest.mark.parametrize("filename,content_type", REJECTED_EXTENSIONS)
def test_upload_unsupported_formats_rejected(client, _setup, user_auth, filename, content_type):
    """Images and legacy Office formats are rejected at upload time."""
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    response = _upload(
        client, headers, course_id, filename, b"fake bytes", content_type
    )
    assert response.status_code == 415


def test_upload_unsupported_extension_rejected(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    response = _upload(
        client,
        headers,
        course_id,
        "malware.exe",
        b"MZ fake",
        "application/octet-stream",
    )
    assert response.status_code == 415


def test_upload_oversized_file_rejected(
    client, _setup, user_auth, monkeypatch, tmp_path
):
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "1")
    get_settings.cache_clear()
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    response = _upload(
        client,
        headers,
        course_id,
        "big.pdf",
        b"x" * (2 * 1024 * 1024),
        "application/pdf",
    )
    assert response.status_code == 413


def test_upload_empty_material_rejected(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    response = _upload(
        client, headers, course_id, None, None, None, source_url=None
    )
    assert response.status_code == 400
    assert "either a file or a source_url" in response.json()["detail"]


def test_upload_invalid_course_returned_404(client, _setup, user_auth):
    _, headers = user_auth
    _make_user_and_course(client, headers)
    response = _upload(
        client, headers, str(uuid.uuid4()), "notes.pdf", b"pdf", "application/pdf"
    )
    assert response.status_code == 404
    assert "Course" in response.json()["detail"]


def test_upload_requires_authentication(client, _setup):
    data = {
        "course_id": str(uuid.uuid4()),
        "title": "Chapter 1 Notes",
        "material_type": "notes",
    }
    response = client.post("/api/materials/upload", data=data)
    assert response.status_code == 401


def test_upload_url_only_material(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    response = _upload(
        client,
        headers,
        course_id,
        None,
        None,
        None,
        source_url="https://example.com/notes.pdf",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["source_url"] == "https://example.com/notes.pdf"
    assert body["file_name"] is None
    assert body["file_size"] is None


def test_upload_file_and_url_rejected(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    response = _upload(
        client,
        headers,
        course_id,
        "notes.pdf",
        b"pdf",
        "application/pdf",
        source_url="https://example.com/notes.pdf",
    )
    assert response.status_code == 400
    assert "not both" in response.json()["detail"]


def test_upload_original_filename_sanitized(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    response = _upload(
        client,
        headers,
        course_id,
        "../../notes.pdf",
        b"pdf",
        "application/pdf",
    )
    assert response.status_code == 201
    assert response.json()["file_name"] == "notes.pdf"


def test_file_is_stored_with_safe_name(client, _setup, db, user_auth):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    content = b"stored bytes check"
    body = _upload(
        client, headers, course_id, "notes.pdf", content, "application/pdf"
    ).json()
    stored_name = _stored_name(db, uuid.UUID(body["id"]))
    stored_path = get_settings().storage_dir / stored_name
    assert stored_path.is_file()
    assert stored_path.read_bytes() == content
    assert ".." not in stored_name
    assert "/" not in stored_name
    assert "\\" not in stored_name


def test_download_returns_correct_file(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    content = b"%PDF-1.4 downloadable"
    body = _upload(
        client, headers, course_id, "notes.pdf", content, "application/pdf"
    ).json()

    response = client.get(f"/api/materials/{body['id']}/download", headers=headers)
    assert response.status_code == 200
    assert response.content == content
    assert "attachment" in response.headers["content-disposition"]
    assert "notes.pdf" in response.headers["content-disposition"]


def test_download_missing_material_returned_404(client, _setup, user_auth):
    _, headers = user_auth
    response = client.get(
        f"/api/materials/{uuid.uuid4()}/download", headers=headers
    )
    assert response.status_code == 404


def test_download_url_based_material_returns_metadata(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    body = _upload(
        client,
        headers,
        course_id,
        None,
        None,
        None,
        source_url="https://example.com/book.pdf",
    ).json()
    response = client.get(f"/api/materials/{body['id']}/download", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["source_url"] == "https://example.com/book.pdf"
    assert "no local file" in payload["detail"]


def test_delete_removes_record_and_file(client, _setup, db, user_auth):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    body = _upload(
        client, headers, course_id, "notes.pdf", b"pdf", "application/pdf"
    ).json()
    stored_file = get_settings().storage_dir / _stored_name(
        db, uuid.UUID(body["id"])
    )
    assert stored_file.is_file()

    response = client.delete(f"/api/materials/{body['id']}", headers=headers)
    assert response.status_code == 204
    assert not stored_file.exists()

    response = client.get(f"/api/materials/{body['id']}", headers=headers)
    assert response.status_code == 404


def test_delete_handles_missing_stored_file_gracefully(
    client, _setup, db, user_auth
):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    body = _upload(
        client, headers, course_id, "notes.pdf", b"pdf", "application/pdf"
    ).json()
    stored_file = get_settings().storage_dir / _stored_name(
        db, uuid.UUID(body["id"])
    )
    stored_file.unlink()

    response = client.delete(f"/api/materials/{body['id']}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"/api/materials/{body['id']}", headers=headers).status_code == 404


def test_path_traversal_blocked_by_resolver(_setup):
    from app.core.storage import resolve_file_path

    for evil in ("../secret.txt", "..\\secret.txt", "/etc/passwd", "C:\\windows\\x"):
        with pytest.raises(ValueError):
            resolve_file_path(evil)


def test_tampered_stored_name_cannot_escape_storage(
    client, _setup, db, user_auth
):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    body = _upload(
        client, headers, course_id, "notes.pdf", b"pdf", "application/pdf"
    ).json()

    material = db.get(StudyMaterial, uuid.UUID(body["id"]))
    material.stored_file_name = "../escaped.txt"
    db.commit()

    response = client.get(f"/api/materials/{body['id']}/download", headers=headers)
    assert response.status_code == 500


def test_existing_list_and_get_include_file_metadata(client, _setup, user_auth):
    _, headers = user_auth
    course_id = _make_user_and_course(client, headers)
    content = b"%PDF-1.4 metadata"
    body = _upload(
        client, headers, course_id, "notes.pdf", content, "application/pdf"
    ).json()

    listing = client.get("/api/materials", headers=headers).json()["items"]
    entry = next(
        material for material in listing if material["id"] == body["id"]
    )
    assert entry["file_name"] == "notes.pdf"
    assert entry["file_size"] == len(content)
    assert entry["mime_type"] == "application/pdf"
    assert entry["status"] == "uploaded"
    assert "source_url" in entry
    assert "created_at" in entry
    assert "updated_at" in entry

    detail = client.get(f"/api/materials/{body['id']}", headers=headers).json()
    assert detail["title"] == "Chapter 1 Notes"