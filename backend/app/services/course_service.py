import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Course, CourseEnrollment, User
from app.schemas.course import CourseCreate
from app.services.errors import (
    AccessDeniedError,
    DuplicateResourceError,
    EnrollmentNotFoundError,
    ResourceNotFoundError,
)
from app.services.pagination import escape_like


def _get_teacher_or_404(db: Session, teacher_id: uuid.UUID) -> User:
    teacher = db.get(User, teacher_id)
    if teacher is None:
        raise ResourceNotFoundError("Teacher", teacher_id)
    return teacher


def create_course(
    db: Session, payload: CourseCreate, *, teacher_id: uuid.UUID
) -> Course:
    """Create a course owned by the authenticated teacher.

    The teacher identity always comes from the caller (derived from the JWT),
    never from the request payload.
    """
    _get_teacher_or_404(db, teacher_id)

    existing = db.scalar(select(Course).where(Course.code == payload.code))
    if existing is not None:
        raise DuplicateResourceError("A course with this code already exists")

    course = Course(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        teacher_id=teacher_id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def list_courses(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
) -> tuple[int, list[Course]]:
    """List courses with optional case-insensitive name/code search.

    Returns ``(total, items)`` where ``total`` is the number of matching
    courses before pagination is applied.
    """
    conditions = []
    if search:
        pattern = f"%{escape_like(search)}%"
        conditions.append(
            or_(Course.name.ilike(pattern), Course.code.ilike(pattern))
        )

    total = db.scalar(
        select(func.count()).select_from(Course).where(*conditions)
    )

    query = select(Course).options(selectinload(Course.teacher))
    if conditions:
        query = query.where(*conditions)
    query = (
        query.order_by(Course.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    items = list(db.scalars(query).all())
    return int(total or 0), items


def list_courses_for_user(
    db: Session,
    *,
    user: User,
    page: int,
    page_size: int,
    search: str | None = None,
) -> tuple[int, list[Course]]:
    """List the courses a user owns (teacher) or is enrolled in (student).

    Supports the same ``page``/``page_size``/``search`` contract as
    :func:`list_courses`, but the result is always scoped to the caller so a
    profile/dashboard page never has to filter the full catalog client-side.
    """
    if user.role == "teacher":
        base_condition = Course.teacher_id == user.id
    elif user.role == "student":
        base_condition = Course.id.in_(
            select(CourseEnrollment.course_id).where(
                CourseEnrollment.student_id == user.id
            )
        )
    else:
        return 0, []

    conditions = [base_condition]
    if search:
        pattern = f"%{escape_like(search)}%"
        conditions.append(
            or_(Course.name.ilike(pattern), Course.code.ilike(pattern))
        )

    total = db.scalar(
        select(func.count()).select_from(Course).where(*conditions)
    )

    query = (
        select(Course)
        .options(selectinload(Course.teacher))
        .where(*conditions)
        .order_by(Course.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    items = list(db.scalars(query).all())
    return int(total or 0), items


def get_course(db: Session, course_id: uuid.UUID) -> Course:
    course = db.get(
        Course, course_id, options=[selectinload(Course.teacher)]
    )
    if course is None:
        raise ResourceNotFoundError("Course", course_id)
    return course


def is_course_owner(user: User, course: Course) -> bool:
    return course.teacher_id is not None and course.teacher_id == user.id


def require_course_owner(
    db: Session, course_id: uuid.UUID, user: User
) -> Course:
    """Return the course only when the given user is the owning teacher."""
    course = get_course(db, course_id)
    if not is_course_owner(user, course):
        raise AccessDeniedError("Not authorized to manage this course")
    return course


def get_enrollment(
    db: Session, course_id: uuid.UUID, student_id: uuid.UUID
) -> CourseEnrollment | None:
    return db.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == student_id,
        )
    )


def is_enrolled(
    db: Session, course_id: uuid.UUID, student_id: uuid.UUID
) -> bool:
    return get_enrollment(db, course_id, student_id) is not None


def enroll_student(
    db: Session, course_id: uuid.UUID, student: User
) -> CourseEnrollment:
    """Enroll a student in a course. The student identity is the caller."""
    course = get_course(db, course_id)
    if student.role != "student":
        raise AccessDeniedError("Only students can enroll in courses")

    if get_enrollment(db, course.id, student.id) is not None:
        raise DuplicateResourceError("Already enrolled in this course")

    enrollment = CourseEnrollment(course_id=course.id, student_id=student.id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def unenroll_student(
    db: Session, course_id: uuid.UUID, student_id: uuid.UUID
) -> None:
    """Remove a student's own enrollment from a course."""
    get_course(db, course_id)
    enrollment = get_enrollment(db, course_id, student_id)
    if enrollment is None:
        raise EnrollmentNotFoundError("You are not enrolled in this course")

    db.delete(enrollment)
    db.commit()


def list_enrolled_students(
    db: Session, course_id: uuid.UUID
) -> list[CourseEnrollment]:
    """Return enrollments (with student info) for a course."""
    get_course(db, course_id)
    return list(
        db.scalars(
            select(CourseEnrollment)
            .options(selectinload(CourseEnrollment.student))
            .where(CourseEnrollment.course_id == course_id)
            .order_by(CourseEnrollment.enrolled_at)
        ).all()
    )