"""Database-backed search tests for courses and study materials."""
import pytest

from app.core.config import get_settings


def _create_course(client, headers, code, name):
    response = client.post(
        "/api/courses", json={"name": name, "code": code}, headers=headers
    )
    assert response.status_code == 201
    return response.json()["id"]


def _upload(client, headers, course_id, filename, title):
    return client.post(
        "/api/materials/upload",
        data={"course_id": course_id, "title": title, "material_type": "notes"},
        files={"file": (filename, b"%PDF-1.4 fake", "application/pdf")},
        headers=headers,
    )


@pytest.fixture()
def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_course_search_matches_name(client, teacher_auth):
    _, headers = teacher_auth
    _create_course(client, headers, "CS301", "Introduction to Databases")

    response = client.get("/api/courses?search=databases", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["code"] == "CS301"


def test_course_search_matches_code(client, teacher_auth):
    _, headers = teacher_auth
    _create_course(client, headers, "CS301", "Databases")
    _create_course(client, headers, "MATH201", "Linear Algebra")

    response = client.get("/api/courses?search=CS301", headers=headers)
    items = response.json()["items"]
    assert [c["code"] for c in items] == ["CS301"]


def test_course_search_is_case_insensitive(client, teacher_auth):
    _, headers = teacher_auth
    _create_course(client, headers, "PHY101", "Physics for Engineers")

    for term in ("PHYSICS", "physics", "Physics"):
        response = client.get(f"/api/courses?search={term}", headers=headers)
        assert response.json()["total"] == 1, term


def test_course_search_no_match(client, teacher_auth):
    _, headers = teacher_auth
    _create_course(client, headers, "CS301", "Databases")

    response = client.get("/api/courses?search=zzzzz", headers=headers)
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_course_search_combined_with_pagination(client, teacher_auth):
    _, headers = teacher_auth
    _create_course(client, headers, "CS301", "Databases I")
    _create_course(client, headers, "CS302", "Databases II")
    _create_course(client, headers, "MATH201", "Linear Algebra")

    response = client.get(
        "/api/courses?search=databases&page=1&page_size=1", headers=headers
    )
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["total_pages"] == 2

    page2 = client.get(
        "/api/courses?search=databases&page=2&page_size=1", headers=headers
    ).json()
    assert len(page2["items"]) == 1
    assert page2["items"][0]["id"] != body["items"][0]["id"]


def test_material_search_matches_title(
    client, _setup, teacher_auth
):
    _, headers = teacher_auth
    course_id = _create_course(client, headers, "CS301", "Databases")
    _upload(client, headers, course_id, "syllabus.pdf", "Midterm Exam Notes")

    response = client.get("/api/materials?search=midterm", headers=headers)
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Midterm Exam Notes"


def test_material_search_matches_original_filename(client, _setup, teacher_auth):
    _, headers = teacher_auth
    course_id = _create_course(client, headers, "CS301", "Databases")
    _upload(client, headers, course_id, "lecture-notes.pdf", "Chapter One")

    response = client.get("/api/materials?search=lecture", headers=headers)
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["file_name"] == "lecture-notes.pdf"


def test_material_search_combines_with_course_filter(
    client, _setup, teacher_auth
):
    _, headers = teacher_auth
    course_a = _create_course(client, headers, "CS301", "Databases")
    course_b = _create_course(client, headers, "MATH201", "Linear Algebra")

    _upload(client, headers, course_a, "first.pdf", "Algebra Basics")
    _upload(client, headers, course_b, "second.pdf", "Algebra Advanced")

    response = client.get(
        f"/api/materials?course_id={course_a}&search=algebra", headers=headers
    )
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Algebra Basics"


def test_material_search_with_type_and_pagination(
    client, _setup, teacher_auth
):
    _, headers = teacher_auth
    course_id = _create_course(client, headers, "CS301", "Databases")
    for i in range(3):
        _upload(client, headers, course_id, f"note{i}.pdf", f"Database Notes {i}")

    response = client.get(
        "/api/materials?search=database&page=1&page_size=2", headers=headers
    )
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["total_pages"] == 2


def test_material_search_no_match(client, _setup, teacher_auth):
    _, headers = teacher_auth
    course_id = _create_course(client, headers, "CS301", "Databases")
    _upload(client, headers, course_id, "syllabus.pdf", "Syllabus")

    response = client.get("/api/materials?search=quantum", headers=headers)
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_material_search_empty_query_returns_all(client, teacher_auth):
    _, headers = teacher_auth
    course_id = _create_course(client, headers, "CS301", "Databases")
    _upload(client, headers, course_id, "a.pdf", "Alpha")
    _upload(client, headers, course_id, "b.pdf", "Beta")

    response = client.get("/api/materials?search=", headers=headers)
    assert response.json()["total"] == 2