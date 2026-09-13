import uuid

from app.models import Course, User
from tests.conftest import auth_headers_for, make_db_user


def _create_course(client, headers, name="Databases", code="CS301"):
    return client.post(
        "/api/courses", json={"name": name, "code": code}, headers=headers
    )


def test_teacher_creates_course_and_becomes_owner(client, teacher_auth, db):
    user_id, headers = teacher_auth
    response = _create_course(client, headers)
    assert response.status_code == 201
    body = response.json()
    assert body["teacher_id"] == str(user_id)
    assert body["teacher"]["id"] == str(user_id)

    course = db.get(Course, uuid.UUID(body["id"]))
    assert course is not None
    assert course.teacher_id == user_id


def test_client_cannot_impersonate_another_teacher(client, teacher_auth, db):
    user_id, headers = teacher_auth
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
    assert response.json()["teacher_id"] == str(user_id)
    assert response.json()["teacher_id"] != other_id
    course = db.get(Course, uuid.UUID(response.json()["id"]))
    assert course.teacher_id == user_id


def test_student_cannot_create_course(client, student_auth):
    _, headers = student_auth
    response = _create_course(client, headers)
    assert response.status_code == 403


def test_teacher_cannot_create_course_owned_by_another_teacher(client):
    other = make_db_user(name="Other", email="other@example.com", role="teacher")
    other_headers = auth_headers_for(other)
    response = client.post(
        "/api/courses",
        json={"name": "Databases", "code": "CS301"},
        headers=other_headers,
    )
    assert response.status_code == 201
    assert response.json()["teacher_id"] == str(other.id)


def test_course_response_exposes_owner(client, teacher_auth):
    user_id, headers = teacher_auth
    course_id = _create_course(client, headers).json()["id"]
    response = client.get(f"/api/courses/{course_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["teacher_id"] == str(user_id)
    assert body["teacher"]["email"] == "teacher@example.com"
    assert "password_hash" not in body["teacher"]


def test_list_courses_exposes_owner(client, teacher_auth):
    user_id, headers = teacher_auth
    _create_course(client, headers, name="Alpha", code="A101")
    response = client.get("/api/courses", headers=headers)
    assert response.status_code == 200
    entry = next(
        c for c in response.json()["items"] if c["code"] == "A101"
    )
    assert entry["teacher_id"] == str(user_id)
    assert entry["teacher"]["name"] == "Teacher"


def test_non_owner_teacher_cannot_view_students(client):
    owner = make_db_user(name="Owner", email="owner@example.com", role="teacher")
    other = make_db_user(name="Other", email="other@example.com", role="teacher")
    owner_headers = auth_headers_for(owner)
    other_headers = auth_headers_for(other)

    course_id = _create_course(client, owner_headers).json()["id"]
    response = client.get(
        f"/api/courses/{course_id}/students", headers=other_headers
    )
    assert response.status_code == 403


def test_student_cannot_view_enrolled_students(client, teacher_auth, student_auth):
    _, teacher_headers = teacher_auth
    _, student_headers = student_auth
    course_id = _create_course(client, teacher_headers).json()["id"]
    response = client.get(
        f"/api/courses/{course_id}/students", headers=student_headers
    )
    assert response.status_code == 403


def test_course_owner_can_view_enrolled_students(
    client, teacher_auth, student_auth
):
    _, teacher_headers = teacher_auth
    student_id, student_headers = student_auth
    course_id = _create_course(client, teacher_headers).json()["id"]

    assert (
        client.post(
            f"/api/courses/{course_id}/enroll", headers=student_headers
        ).status_code
        == 201
    )

    response = client.get(
        f"/api/courses/{course_id}/students", headers=teacher_headers
    )
    assert response.status_code == 200
    students = response.json()
    assert len(students) == 1
    assert students[0]["id"] == str(student_id)
    assert students[0]["email"] == "student@example.com"
    assert "password_hash" not in students[0]


def test_student_list_is_empty_before_enrollment(client, teacher_auth):
    _, headers = teacher_auth
    course_id = _create_course(client, headers).json()["id"]
    response = client.get(
        f"/api/courses/{course_id}/students", headers=headers
    )
    assert response.status_code == 200
    assert response.json() == []


def test_authenticated_users_can_view_allowed_course_info(client, teacher_auth):
    _, teacher_headers = teacher_auth
    course_id = _create_course(client, teacher_headers).json()["id"]

    other = make_db_user(name="Viewer", email="viewer@example.com", role="student")
    response = client.get(
        f"/api/courses/{course_id}", headers=auth_headers_for(other)
    )
    assert response.status_code == 200
    assert response.json()["id"] == course_id


def test_course_owner_response_has_no_sensitive_fields(client, teacher_auth):
    _, headers = teacher_auth
    body = _create_course(client, headers).json()
    assert "password_hash" not in body
    assert "password_hash" not in body["teacher"]