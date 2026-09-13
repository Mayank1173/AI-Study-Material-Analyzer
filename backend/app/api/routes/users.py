import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_teacher
from app.db.session import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services import user_service
from app.services.errors import DuplicateResourceError, ResourceNotFoundError

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.post(
    "", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher),
):
    """Create a new user. Teacher-only; public signup uses /api/auth/register."""
    try:
        return user_service.create_user(db, payload)
    except DuplicateResourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher),
):
    """Retrieve a single user by ID. Teacher-only to limit enumeration."""
    try:
        return user_service.get_user(db, user_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc