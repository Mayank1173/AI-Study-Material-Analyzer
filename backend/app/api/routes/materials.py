import uuid
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import get_settings
from app.core.storage import resolve_file_path
from app.db.session import get_db
from app.models import User
from app.schemas.common import PaginatedResponse
from app.schemas.study_material import (
    MaterialStatus,
    StudyMaterialCreate,
    StudyMaterialResponse,
)
from app.services import study_material_service
from app.services.errors import (
    AccessDeniedError,
    FileTooLargeError,
    ResourceNotFoundError,
    UnsupportedFileTypeError,
)
from app.services.pagination import total_pages
from rag.knowledge_base import KnowledgeBase, get_knowledge_base

router = APIRouter(prefix="/api/materials", tags=["Study Materials"])


def get_processing_knowledge_base() -> KnowledgeBase:
    """Return a KnowledgeBase for processing/deletion. Overrideable in tests."""
    return get_knowledge_base()


def _not_found(exc):
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
    ) from exc


def _forbidden(exc):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
    ) from exc


@router.post(
    "",
    response_model=StudyMaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_study_material(
    payload: StudyMaterialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new study material record.

    The uploader identity is taken from the authenticated user, never from the
    request body. The target course must exist.
    """
    try:
        return study_material_service.create_study_material(
            db, payload, uploaded_by=current_user.id
        )
    except ResourceNotFoundError as exc:
        _not_found(exc)


@router.post(
    "/upload",
    response_model=StudyMaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_study_material(
    course_id: uuid.UUID = Form(...),
    title: str = Form(..., min_length=1, max_length=255),
    material_type: str = Form(..., min_length=1, max_length=50),
    file: UploadFile | None = File(default=None),
    source_url: str | None = Form(default=None, max_length=2048),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Upload a study-material file or register a URL-based material.

    Any authenticated user can upload. The uploader identity comes from the
    access token and the target course must exist.
    """
    if file is None and not source_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A material requires either a file or a source_url",
        )
    if file is not None and source_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either a file or a source_url, not both",
        )

    try:
        if file is not None:
            max_bytes = get_settings().max_upload_size_mb * 1024 * 1024
            return study_material_service.upload_file_material(
                db,
                course_id=course_id,
                uploaded_by=current_user.id,
                title=title,
                material_type=material_type,
                file=file,
                max_upload_size_bytes=max_bytes,
            )
        return study_material_service.create_url_material(
            db,
            course_id=course_id,
            uploaded_by=current_user.id,
            title=title,
            material_type=material_type,
            source_url=source_url,
        )
    except ResourceNotFoundError as exc:
        _not_found(exc)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)
        ) from exc


@router.get("", response_model=PaginatedResponse[StudyMaterialResponse])
def list_study_materials(
    course_id: uuid.UUID | None = Query(default=None),
    material_type: str | None = Query(default=None, max_length=50),
    status: MaterialStatus | None = Query(
        default=None,
        description="Filter by processing status; invalid values return 422",
    ),
    search: str | None = Query(
        default=None,
        max_length=255,
        description="Case-insensitive search over title and original filename",
    ),
    page: int = Query(
        default=1, ge=1, description="Page number, starting at 1"
    ),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Items per page (max 100)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List the study materials uploaded by the authenticated user.

    Optionally filtered by course, type, or status, and searched by title or
    original filename. Results are always scoped to the caller's own uploads
    and are paginated.
    """
    try:
        total, materials = study_material_service.list_study_materials(
            db,
            user=current_user,
            course_id=course_id,
            material_type=material_type,
            status=status,
            search=search,
            page=page,
            page_size=page_size,
        )
        return PaginatedResponse[StudyMaterialResponse](
            items=materials,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages(total, page_size),
        )
    except ResourceNotFoundError as exc:
        _not_found(exc)
    except AccessDeniedError as exc:
        _forbidden(exc)


@router.get("/{material_id}", response_model=StudyMaterialResponse)
def get_study_material(
    material_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve a single study material by ID.

    Only the user who uploaded the material may access it.
    """
    try:
        material = study_material_service.get_study_material(db, material_id)
        study_material_service.assert_owns_material(current_user, material)
        return material
    except ResourceNotFoundError as exc:
        _not_found(exc)
    except AccessDeniedError as exc:
        _forbidden(exc)


@router.get("/{material_id}/download")
def download_study_material(
    material_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Download the stored file for a study material, where one exists.

    Only the user who uploaded the material may access it.
    """
    try:
        material = study_material_service.get_study_material(db, material_id)
        study_material_service.assert_owns_material(current_user, material)
    except ResourceNotFoundError as exc:
        _not_found(exc)
    except AccessDeniedError as exc:
        _forbidden(exc)

    if material.stored_file_name:
        try:
            path: Path = resolve_file_path(material.stored_file_name)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored file reference is invalid",
            ) from None
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stored file not found for this material",
            )
        return FileResponse(
            path,
            media_type=material.mime_type or "application/octet-stream",
            filename=material.file_name,
        )

    if material.source_url:
        return {
            "material_id": str(material.id),
            "detail": "This material is URL-based and has no local file to download",
            "source_url": material.source_url,
        }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No file is available for this material",
    )


@router.post(
    "/{material_id}/process",
    response_model=StudyMaterialResponse,
)
def process_study_material(
    material_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    knowledge_base: KnowledgeBase = Depends(get_processing_knowledge_base),
):
    """Start (or restart) processing for a study material.

    Only the user who uploaded the material may trigger processing. Only
    freshly uploaded or failed materials may be moved into ``processing``.
    The material is indexed into the RAG knowledge base.
    """
    try:
        material = study_material_service.get_study_material(db, material_id)
        study_material_service.assert_owns_material(current_user, material)
    except ResourceNotFoundError as exc:
        _not_found(exc)
    except AccessDeniedError as exc:
        _forbidden(exc)

    if material.status not in ("uploaded", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only freshly uploaded or failed materials can start processing",
        )

    return study_material_service.process_material(
        db, material_id, knowledge_base=knowledge_base
    )


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_study_material(
    material_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    knowledge_base: KnowledgeBase = Depends(get_processing_knowledge_base),
) -> None:
    """Delete a study material by ID, including its stored file and RAG chunks.

    Only the user who uploaded the material may delete it.
    """
    try:
        material = study_material_service.get_study_material(db, material_id)
        study_material_service.assert_owns_material(current_user, material)
    except ResourceNotFoundError as exc:
        _not_found(exc)
    except AccessDeniedError as exc:
        _forbidden(exc)

    study_material_service.delete_study_material(
        db, material_id, knowledge_base=knowledge_base
    )