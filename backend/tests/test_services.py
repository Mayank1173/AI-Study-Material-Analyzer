import uuid

import pytest

from app.models import Course, StudyMaterial, User
from app.schemas.course import CourseCreate
from app.schemas.study_material import StudyMaterialCreate
from app.services import course_service, study_material_service
from app.services.errors import AccessDeniedError, DuplicateResourceError, ResourceNotFoundError


def _make_user(db_session, *, name="Alice", email=None):
    if email is None:
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    user = User(name=name, email=email, role="student")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_course(db_session, owner=None):
    if owner is None:
        owner = _make_user(db_session)
    return course_service.create_course(
        db_session,
        CourseCreate(name="Databases", code="CS301"),
        owner_id=owner.id,
    )


def _material_payload(course_id):
    return StudyMaterialCreate(
        course_id=course_id,
        title="Notes",
        material_type="notes",
    )


def test_service_create_course_and_duplicate_code(db_session):
    owner = _make_user(db_session, name="Owner", email="owner@example.com")
    course = _make_course(db_session, owner)
    assert isinstance(course.id, uuid.UUID)

    with pytest.raises(DuplicateResourceError):
        course_service.create_course(
            db_session,
            CourseCreate(name="Databases 2", code="CS301"),
            owner_id=owner.id,
        )


def test_service_same_code_allowed_across_owners(db_session):
    alice = _make_user(db_session, name="Alice", email="alice@example.com")
    bob = _make_user(db_session, name="Bob", email="bob@example.com")
    _make_course(db_session, alice)
    second = _make_course(db_session, bob)
    assert second.code == "CS301"


def test_service_get_missing_course_raises_not_found(db_session):
    with pytest.raises(ResourceNotFoundError):
        course_service.get_course(db_session, uuid.uuid4())


def test_service_create_material_rejects_bad_references(db_session):
    course = _make_course(db_session)
    user = _make_user(db_session)

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
    course = _make_course(db_session)
    user = _make_user(db_session)
    material = study_material_service.create_study_material(
        db_session,
        _material_payload(course.id),
        uploaded_by=user.id,
    )
    assert material.status == "uploaded"
    assert material.uploaded_by == user.id


def test_service_delete_material_removes_record(db_session):
    course = _make_course(db_session)
    user = _make_user(db_session)
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


def test_service_assert_owns_material(db_session):
    course = _make_course(db_session)
    owner = _make_user(db_session, name="Owner", email="owner@example.com")
    other = _make_user(db_session, name="Other", email="other@example.com")
    material = study_material_service.create_study_material(
        db_session,
        _material_payload(course.id),
        uploaded_by=owner.id,
    )

    study_material_service.assert_owns_material(owner, material)
    with pytest.raises(AccessDeniedError):
        study_material_service.assert_owns_material(other, material)