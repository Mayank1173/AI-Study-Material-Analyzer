"""Tests for the GET /api/courses/mine endpoint.

Teachers should see only the courses they own; students should see only the
courses they are enrolled in.
"""
import pytest

from tests.conftest import auth_headers_for, make_db_user


def _course(client, headers, name, code):
    return client.post(
        "/api/courses", json={"name": name, "code": code}, headers=headers
    )


def _enroll(client, course_id, student_headers):
    return client.post(f"/api/courses/{course_id}/enroll", headers=student_headers)


# ---------------- Teacher view ----------------


def test_teacher_sees_only_owned_courses(client):
    alice = make_db_user(name="Alice", email="alice@example.com", role="teacher")
    bob = make_db_user(name="Bob", email="bob@example.com", role="teacher")
    alice_headers = auth_headers_for(alice)
    bob_headers = auth_headers_for(bob)

    _course(client, alice_headers, "Databases I", "CS301")
    _course(client, bob_headers, "Databases II", "CS302")
    _course(client, alice_headers, "OS", "CS305")

    response = client.get("/api/courses/mine", headers=alice_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    codes = {c["code"] for c in body["items"]}
    assert codes == {"CS301", "CS305"}


# ---------------- Student view ----------------


def test_student_sees_only_enrolled_courses(client, teacher_auth):
    _, teacher_headers = teacher_auth
    course1 = _course(
        client, teacher_headers, "Databases I", "CS301"
    ).json()["id"]
    course2 = _course(
        client, teacher_headers, "Databases II", "CS302"
    ).json()["id"]

    viewer = make_db_user(name="Viewer", email="viewer@example.com", role="student")
    viewer_headers = auth_headers_for(viewer)
    assert _enroll(client, course1, viewer_headers).status_code == 201

    response = client.get("/api/courses/mine", headers=viewer_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == course1


def test_unenrolled_student_my_courses_empty(client, teacher_auth, student_auth):
    _, teacher_headers = teacher_auth
    _, student_headers = student_auth
    _course(client, teacher_headers, "Databases", "CS301")

    response = client.get("/api/courses/mine", headers=student_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["total_pages"] == 0


# ---------------- Pagination / search ----------------


def test_my_courses_pagination_envelope(client, teacher_auth):
    _, headers = teacher_auth
    for i in range(5):
        _course(client, headers, name=f"Course {i}", code=f"MINE{i}")

    response = client.get(
        "/api/courses/mine?page=1&page_size=2", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 5
    assert body["total_pages"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2


def test_my_courses_search_scoped(client):
    alice = make_db_user(name="Alice", email="alice@example.com", role="teacher")
    bob = make_db_user(name="Bob", email="bob@example.com", role="teacher")
    alice_headers = auth_headers_for(alice)
    bob_headers = auth_headers_for(bob)

    _course(client, alice_headers, "Databases I", "CS301")
    _course(client, bob_headers, "Databases II", "CS302")

    response = client.get("/api/courses/mine?search=Databases", headers=alice_headers)
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["code"] == "CS301"


# ---------------- Auth required ----------------


def test_my_courses_requires_authentication(client):
    assert client.get("/api/courses/mine").status_code == 401


# ---------------- Envelope consistency ----------------


def test_my_courses_envelope_keys(client, teacher_auth):
    _, headers = teacher_auth
    _course(client, headers, "Databases", "CS301")
    body = client.get("/api/courses/mine", headers=headers).json()
    assert set(body.keys()) == {
        "items",
        "page",
        "page_size",
        "total",
        "total_pages",
    }
