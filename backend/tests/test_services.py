import uuid

import pytest

from app.models import Course, StudyMaterial, User
from app.schemas.course import CourseCreate
from app.schemas.study_material import StudyMaterialCreate
from app.schemas.user import UserCreate
from app.services import course_service, study_material_service, user_service
from app.services.errors import DuplicateResourceError, ResourceNotFoundError


def _user(db_session):
    return user_service.create_user(
        db_session, UserCreate(name="Alice", email="alice@example.com")
    )


def _teacher(db_session, email="prof_alice@example.com"):
    teacher = User(
        name="Prof. Alice",
        email=email,
        role="teacher",
    )
    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)
    return teacher


def _course(db_session):
    teacher = _teacher(db_session)
    return course_service.create_course(
        db_session,
        CourseCreate(name="Databases", code="CS301"),
        teacher_id=teacher.id,
    )


def _material_payload(course_id):
    return StudyMaterialCreate(
        course_id=course_id,
        title="Notes",
        material_type="notes",
    )


def test_service_create_user_and_duplicate_email(db_session):
    user = _user(db_session)
    assert isinstance(user.id, uuid.UUID)
    assert user.role == "student"
    assert user.password_hash is None

    with pytest.raises(DuplicateResourceError):
        user_service.create_user(
            db_session, UserCreate(name="Alice 2", email="alice@example.com")
        )


def test_service_create_course_and_duplicate_code(db_session):
    course = _course(db_session)
    assert isinstance(course.id, uuid.UUID)

    teacher = _teacher(db_session, email="dup_prof@example.com")
    with pytest.raises(DuplicateResourceError):
        course_service.create_course(
            db_session,
            CourseCreate(name="Databases 2", code="CS301"),
            teacher_id=teacher.id,
        )


def test_service_get_missing_course_raises_not_found(db_session):
    with pytest.raises(ResourceNotFoundError):
        course_service.get_course(db_session, uuid.uuid4())


def test_service_create_material_rejects_bad_references(db_session):
    course = _course(db_session)
    user = _user(db_session)

    with pytest.raises(ResourceNotFoundError):
        study_material_service.create_study_material(
            db_session,
            _material_payload(course.id),
            uploaded_by=uuid.uuid4(),
        )

    with pytest.raises(ResourceNotFoundError):
        study_material_service.create_study_material(
            db_session,
            _material_payload(uuid.uuid4()),
            uploaded_by=user.id,
        )


def test_service_material_uses_default_status_when_omitted(db_session):
    course = _course(db_session)
    user = _user(db_session)
    material = study_material_service.create_study_material(
        db_session,
        _material_payload(course.id),
        uploaded_by=user.id,
    )
    assert material.status == "uploaded"
    assert material.uploaded_by == user.id


def test_service_delete_material_removes_record(db_session):
    course = _course(db_session)
    user = _user(db_session)
    material = study_material_service.create_study_material(
        db_session,
        _material_payload(course.id),
        uploaded_by=user.id,
    )
    material_id = material.id

    study_material_service.delete_study_material(db_session, material_id)

    assert db_session.get(StudyMaterial, material_id) is None
    assert db_session.get(User, user.id) is not None
    assert db_session.get(Course, course.id) is not None