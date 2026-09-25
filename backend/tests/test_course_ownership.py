import uuid

from app.models import Course
from tests.conftest import auth_headers_for, make_db_user


def _create_course(client, headers, name="Databases", code="CS301"):
    return client.post(
        "/api/courses", json={"name": name, "code": code}, headers=headers
    )


def test_user_creates_course_and_becomes_creator(client, user_auth, db):
    user_id, headers = user_auth
    response = _create_course(client, headers)
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert "teacher_id" not in body
    assert "teacher" not in body

    course = db.get(Course, uuid.UUID(body["id"]))
    assert course is not None
    assert course.teacher_id == user_id


def test_client_cannot_impersonate_creator(client, user_auth, db):
    user_id, headers = user_auth
    other_id = str(uuid.uuid4())
    response = client.post(
        "/api/courses",
        json={
            "name": "Databases",
            "code": "CS301",
            "teacher_id": other_id,
        },
        headers=headers,
    )
    assert response.status_code == 201
    course = db.get(Course, uuid.UUID(response.json()["id"]))
    assert course.teacher_id == user_id
    assert str(course.teacher_id) != other_id


def test_course_response_does_not_expose_owner(client, user_auth):
    _, headers = user_auth
    body = _create_course(client, headers).json()
    assert "teacher_id" not in body
    assert "teacher" not in body
    assert "password_hash" not in body


def test_list_courses_does_not_expose_owner(client, user_auth):
    _, headers = user_auth
    _create_course(client, headers, name="Alpha", code="A101")
    response = client.get("/api/courses", headers=headers)
    assert response.status_code == 200
    entry = next(
        c for c in response.json()["items"] if c["code"] == "A101"
    )
    assert "teacher_id" not in entry
    assert "teacher" not in entry


def test_duplicate_code_within_owner_returns_409(client, user_auth):
    _, headers = user_auth
    assert _create_course(client, headers).status_code == 201
    response = _create_course(client, headers, name="Databases 2")
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_duplicate_code_across_owners_allowed(client, user_auth, second_user_auth):
    _, first_headers = user_auth
    _, second_headers = second_user_auth
    assert _create_course(client, first_headers).status_code == 201
    response = _create_course(
        client, second_headers, name="Other Databases"
    )
    assert response.status_code == 201


def test_authenticated_user_can_view_any_course(client, user_auth, second_user_auth):
    _, first_headers = user_auth
    course_id = _create_course(client, first_headers).json()["id"]

    _, second_headers = second_user_auth
    response = client.get(f"/api/courses/{course_id}", headers=second_headers)
    assert response.status_code == 200
    assert response.json()["id"] == course_id


def test_unauthenticated_user_cannot_create_course(client):
    response = client.post(
        "/api/courses",
        json={"name": "Databases", "code": "CS301"},
    )
    assert response.status_code == 401