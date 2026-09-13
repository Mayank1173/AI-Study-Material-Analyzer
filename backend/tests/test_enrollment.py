import uuid

import pytest
from sqlalchemy import select

from app.models import Course, CourseEnrollment, User
from app.schemas.course import CourseCreate
from app.services import course_service
from app.services.errors import (
    AccessDeniedError,
    DuplicateResourceError,
    EnrollmentNotFoundError,
    ResourceNotFoundError,
)
from tests.conftest import auth_headers_for, make_db_user


def _course_for_teacher(client, teacher_headers, code="CS301"):
    response = client.post(
        "/api/courses",
        json={"name": "Databases", "code": code},
        headers=teacher_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _enroll(client, course_id, student_headers):
    return client.post(f"/api/courses/{course_id}/enroll", headers=student_headers)


def _enrollment_row(db, course_id, student_id):
    return db.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == student_id,
        )
    )


# ---------------- API tests ----------------


def test_student_enrolls(client, teacher_auth, student_auth, db):
    _, teacher_headers = teacher_auth
    student_id, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)

    response = _enroll(client, course_id, student_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["course_id"] == course_id
    assert body["student_id"] == str(student_id)
    uuid.UUID(body["id"])

    enrollment = _enrollment_row(db, uuid.UUID(course_id), student_id)
    assert enrollment is not None
    assert enrollment.enrolled_at is not None


def test_duplicate_enrollment_returns_409(client, teacher_auth, student_auth):
    _, teacher_headers = teacher_auth
    _, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)

    assert _enroll(client, course_id, student_headers).status_code == 201
    response = _enroll(client, course_id, student_headers)
    assert response.status_code == 409


def test_teacher_cannot_enroll(client, teacher_auth):
    _, teacher_headers = teacher_auth
    course_id = _course_for_teacher(client, teacher_headers)
    response = _enroll(client, course_id, teacher_headers)
    assert response.status_code == 403


def test_student_can_unenroll(client, teacher_auth, student_auth, db):
    _, teacher_headers = teacher_auth
    student_id, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)

    assert _enroll(client, course_id, student_headers).status_code == 201
    assert _enrollment_row(db, uuid.UUID(course_id), student_id) is not None

    response = client.delete(
        f"/api/courses/{course_id}/enroll", headers=student_headers
    )
    assert response.status_code == 204
    assert _enrollment_row(db, uuid.UUID(course_id), student_id) is None


def test_unenroll_without_enrollment_returns_404(
    client, teacher_auth, student_auth
):
    _, teacher_headers = teacher_auth
    _, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)

    response = client.delete(
        f"/api/courses/{course_id}/enroll", headers=student_headers
    )
    assert response.status_code == 404


def test_student_cannot_enroll_another_student(
    client, teacher_auth, student_auth, db
):
    _, teacher_headers = teacher_auth
    student_id, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)

    other = make_db_user(
        name="Other", email="other_student@example.com", role="student"
    )
    response = client.post(
        f"/api/courses/{course_id}/enroll",
        json={"student_id": str(other.id)},
        headers=student_headers,
    )
    assert response.status_code == 201
    assert response.json()["student_id"] == str(student_id)
    assert response.json()["student_id"] != str(other.id)
    assert _enrollment_row(db, uuid.UUID(course_id), other.id) is None


def test_enroll_missing_course_returns_404(client, student_auth):
    _, student_headers = student_auth
    response = _enroll(client, str(uuid.uuid4()), student_headers)
    assert response.status_code == 404


def test_unauthenticated_enroll_returns_401(client):
    response = _enroll(client, str(uuid.uuid4()), {})
    assert response.status_code == 401
    response = client.delete(f"/api/courses/{uuid.uuid4()}/enroll")
    assert response.status_code == 401


def test_enrollment_status_endpoint(client, teacher_auth, student_auth):
    _, teacher_headers = teacher_auth
    _, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)

    url = f"/api/courses/{course_id}/enrollments/me"
    response = client.get(url, headers=student_headers)
    assert response.status_code == 200
    assert response.json()["is_enrolled"] is False
    assert response.json()["enrolled_at"] is None

    assert _enroll(client, course_id, student_headers).status_code == 201
    response = client.get(url, headers=student_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["is_enrolled"] is True
    assert body["enrolled_at"] is not None
    assert body["course_id"] == course_id


def test_enrollment_status_missing_course_returns_404(client, student_auth):
    _, student_headers = student_auth
    response = client.get(
        f"/api/courses/{uuid.uuid4()}/enrollments/me", headers=student_headers
    )
    assert response.status_code == 404


def test_enrollment_response_has_no_sensitive_fields(
    client, teacher_auth, student_auth
):
    _, teacher_headers = teacher_auth
    _, student_headers = student_auth
    course_id = _course_for_teacher(client, teacher_headers)
    body = _enroll(client, course_id, student_headers).json()
    assert set(body.keys()) == {"id", "course_id", "student_id", "enrolled_at"}


# ---------------- Service tests ----------------


def _teacher(db_session):
    teacher = User(
        name="Prof. Smith", email="prof_smith@example.com", role="teacher"
    )
    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)
    return teacher


def _student(db_session, email="stu@example.com"):
    student = User(name="Stud", email=email, role="student")
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


def _service_course(db_session, teacher):
    return course_service.create_course(
        db_session,
        CourseCreate(name="Databases", code="CS301"),
        teacher_id=teacher.id,
    )


def test_service_course_creation_requires_existing_teacher(db_session):
    with pytest.raises(ResourceNotFoundError):
        course_service.create_course(
            db_session,
            CourseCreate(name="Databases", code="CS301"),
            teacher_id=uuid.uuid4(),
        )


def test_service_enroll_student(db_session):
    teacher = _teacher(db_session)
    course = _service_course(db_session, teacher)
    student = _student(db_session)

    enrollment = course_service.enroll_student(db_session, course.id, student)
    assert enrollment.course_id == course.id
    assert enrollment.student_id == student.id
    assert course_service.is_enrolled(db_session, course.id, student.id)


def test_service_duplicate_enrollment_raises(db_session):
    teacher = _teacher(db_session)
    course = _service_course(db_session, teacher)
    student = _student(db_session)

    course_service.enroll_student(db_session, course.id, student)
    with pytest.raises(DuplicateResourceError):
        course_service.enroll_student(db_session, course.id, student)


def test_service_teacher_cannot_enroll(db_session):
    teacher = _teacher(db_session)
    course = _service_course(db_session, teacher)
    with pytest.raises(AccessDeniedError):
        course_service.enroll_student(db_session, course.id, teacher)


def test_service_unenroll_missing_raises(db_session):
    teacher = _teacher(db_session)
    course = _service_course(db_session, teacher)
    student = _student(db_session)
    with pytest.raises(EnrollmentNotFoundError):
        course_service.unenroll_student(db_session, course.id, student.id)


def test_service_enroll_keeps_course_and_user(db_session):
    teacher = _teacher(db_session)
    course = _service_course(db_session, teacher)
    student = _student(db_session)
    enrollment = course_service.enroll_student(db_session, course.id, student)

    course_service.unenroll_student(db_session, course.id, student.id)
    assert db_session.get(Course, course.id) is not None
    assert db_session.get(User, student.id) is not None
    assert db_session.get(CourseEnrollment, enrollment.id) is None