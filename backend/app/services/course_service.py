import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Course, User
from app.schemas.course import CourseCreate
from app.services.errors import DuplicateResourceError, ResourceNotFoundError
from app.services.pagination import escape_like


def _get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise ResourceNotFoundError("User", user_id)
    return user


def create_course(
    db: Session, payload: CourseCreate, *, owner_id: uuid.UUID
) -> Course:
    """Create a subject owned by the authenticated user.

    The owner identity always comes from the caller (derived from the JWT),
    never from the request payload. Codes must be unique within an owner so
    each user can build their own subject library.
    """
    _get_user_or_404(db, owner_id)

    existing = db.scalar(
        select(Course).where(
            Course.teacher_id == owner_id, Course.code == payload.code
        )
    )
    if existing is not None:
        raise DuplicateResourceError("A subject with this code already exists")

    course = Course(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        teacher_id=owner_id,
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

    query = select(Course)
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
    """List the courses (subjects) the user created.

    Supports the same ``page``/``page_size``/``search`` contract as
    :func:`list_courses`, but the result is always scoped to the caller so a
    profile/dashboard page never has to filter the full catalog client-side.
    """
    conditions = [Course.teacher_id == user.id]
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
        .where(*conditions)
        .order_by(Course.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    items = list(db.scalars(query).all())
    return int(total or 0), items


def get_course(db: Session, course_id: uuid.UUID) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise ResourceNotFoundError("Course", course_id)
    return course