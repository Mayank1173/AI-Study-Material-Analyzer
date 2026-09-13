import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_active_user,
    require_student,
    require_teacher,
)
from app.db.session import get_db
from app.models import User
from app.schemas.common import PaginatedResponse
from app.schemas.course import CourseCreate, CourseResponse
from app.schemas.enrollment import (
    EnrolledStudentResponse,
    EnrollmentResponse,
    EnrollmentStatusResponse,
)
from app.services import course_service
from app.services.errors import (
    AccessDeniedError,
    DuplicateResourceError,
    EnrollmentNotFoundError,
    ResourceNotFoundError,
)
from app.services.pagination import total_pages

router = APIRouter(prefix="/api/courses", tags=["Courses"])


@router.post(
    "", response_model=CourseResponse, status_code=status.HTTP_201_CREATED
)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    """Create a new course owned by the authenticated teacher.

    Teacher-only. The owner identity comes from the access token and can never
    be supplied by the client.
    """
    try:
        return course_service.create_course(
            db, payload, teacher_id=current_user.id
        )
    except DuplicateResourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.get("", response_model=PaginatedResponse[CourseResponse])
def list_courses(
    page: int = Query(
        default=1, ge=1, description="Page number, starting at 1"
    ),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Items per page (max 100)"
    ),
    search: str | None = Query(
        default=None,
        max_length=255,
        description="Case-insensitive search over course name and code",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all courses. Any authenticated user.

    Results are paginated and can be filtered with a free-text ``search`` term
    matched case-insensitively against the course name or code.
    """
    total, courses = course_service.list_courses(
        db, page=page, page_size=page_size, search=search
    )
    return PaginatedResponse[CourseResponse](
        items=courses,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages(total, page_size),
    )


@router.get("/mine", response_model=PaginatedResponse[CourseResponse])
def list_my_courses(
    page: int = Query(
        default=1, ge=1, description="Page number, starting at 1"
    ),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Items per page (max 100)"
    ),
    search: str | None = Query(
        default=None,
        max_length=255,
        description="Case-insensitive search over course name and code",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List the caller's own courses.

    Teachers receive the courses they own; students receive the courses they
    are enrolled in. The result is always scoped to the authenticated user.
    Supports the same pagination/search envelope as the full course list.
    """
    total, courses = course_service.list_courses_for_user(
        db, user=current_user, page=page, page_size=page_size, search=search
    )
    return PaginatedResponse[CourseResponse](
        items=courses,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages(total, page_size),
    )


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve a single course by ID. Any authenticated user."""
    try:
        return course_service.get_course(db, course_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get(
    "/{course_id}/students", response_model=list[EnrolledStudentResponse]
)
def list_course_students(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    """List students enrolled in a course. Owning teacher only."""
    try:
        course_service.require_course_owner(db, course_id, current_user)
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except AccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    enrollments = course_service.list_enrolled_students(db, course_id)
    return [
        EnrolledStudentResponse(
            id=enrollment.student.id,
            name=enrollment.student.name,
            email=enrollment.student.email,
            enrolled_at=enrollment.enrolled_at,
        )
        for enrollment in enrollments
    ]


@router.post(
    "/{course_id}/enroll",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def enroll(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Enroll the authenticated student in a course. Student-only."""
    try:
        return course_service.enroll_student(db, course_id, current_user)
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except DuplicateResourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except AccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.delete("/{course_id}/enroll", status_code=status.HTTP_204_NO_CONTENT)
def unenroll(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
) -> None:
    """Remove the authenticated student's enrollment from a course."""
    try:
        course_service.unenroll_student(db, course_id, current_user.id)
    except (ResourceNotFoundError, EnrollmentNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except AccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.get(
    "/{course_id}/enrollments/me",
    response_model=EnrollmentStatusResponse,
)
def my_enrollment(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Report whether the authenticated user is enrolled in the course."""
    try:
        course = course_service.get_course(db, course_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    enrollment = course_service.get_enrollment(db, course.id, current_user.id)
    return EnrollmentStatusResponse(
        course_id=course.id,
        is_enrolled=enrollment is not None,
        enrolled_at=enrollment.enrolled_at if enrollment else None,
    )