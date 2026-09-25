import logging
import uuid
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.file_security import get_extension, sanitize_filename
from app.core.storage import (
    delete_stored_file,
    resolve_file_path,
    save_upload,
    stored_filename_for,
)
from app.models import Course, StudyMaterial, User
from app.schemas.study_material import StudyMaterialCreate
from app.services.errors import AccessDeniedError, ResourceNotFoundError
from app.services.pagination import escape_like

logger = logging.getLogger(__name__)


def assert_owns_material(user: User, material: StudyMaterial) -> None:
    """Materials are private to the user who uploaded them."""
    if material.uploaded_by != user.id:
        raise AccessDeniedError("Not authorized to access this material")


def _ensure_references_exist(
    db: Session, course_id: uuid.UUID, uploaded_by: uuid.UUID
) -> None:
    if db.get(Course, course_id) is None:
        raise ResourceNotFoundError("Course", course_id)
    if db.get(User, uploaded_by) is None:
        raise ResourceNotFoundError("User", uploaded_by)


def create_study_material(
    db: Session, payload: StudyMaterialCreate, *, uploaded_by: uuid.UUID
) -> StudyMaterial:
    _ensure_references_exist(db, payload.course_id, uploaded_by)

    material = StudyMaterial(
        course_id=payload.course_id,
        uploaded_by=uploaded_by,
        title=payload.title,
        material_type=payload.material_type,
        file_name=payload.file_name,
        file_path=payload.file_path,
        source_url=payload.source_url,
    )
    if payload.status is not None:
        material.status = payload.status

    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def list_study_materials(
    db: Session,
    *,
    user: User,
    course_id: uuid.UUID | None = None,
    material_type: str | None = None,
    status: str | None = None,
    search: str | None = None,
    page: int,
    page_size: int,
) -> tuple[int, list[StudyMaterial]]:
    """List the materials uploaded by the authenticated user.

    When a ``course_id`` filter is given the course must exist; the result is
    otherwise always restricted to the caller's own uploads.

    Optional filters (course, type, status) and title/original-file search can
    be combined with pagination. Returns ``(total, items)`` where ``total`` is
    the number of matching materials before pagination is applied.
    """
    conditions = [StudyMaterial.uploaded_by == user.id]
    if course_id is not None:
        if db.get(Course, course_id) is None:
            raise ResourceNotFoundError("Course", course_id)
        conditions.append(StudyMaterial.course_id == course_id)

    if material_type is not None:
        conditions.append(StudyMaterial.material_type == material_type)
    if status is not None:
        conditions.append(StudyMaterial.status == status)
    if search:
        pattern = f"%{escape_like(search)}%"
        conditions.append(
            or_(
                StudyMaterial.title.ilike(pattern),
                StudyMaterial.file_name.ilike(pattern),
            )
        )

    total = db.scalar(
        select(func.count()).select_from(StudyMaterial).where(*conditions)
    )

    query = (
        select(StudyMaterial)
        .where(*conditions)
        .order_by(StudyMaterial.created_at)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(db.scalars(query).all())
    return int(total or 0), items


def get_study_material(db: Session, material_id: uuid.UUID) -> StudyMaterial:
    material = db.get(
        StudyMaterial,
        material_id,
        options=[selectinload(StudyMaterial.course)],
    )
    if material is None:
        raise ResourceNotFoundError("StudyMaterial", material_id)
    return material


def create_url_material(
    db: Session,
    *,
    course_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    title: str,
    material_type: str,
    source_url: str,
) -> StudyMaterial:
    _ensure_references_exist(db, course_id, uploaded_by)

    material = StudyMaterial(
        course_id=course_id,
        uploaded_by=uploaded_by,
        title=title,
        material_type=material_type,
        source_url=source_url,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def upload_file_material(
    db: Session,
    *,
    course_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    title: str,
    material_type: str,
    file: UploadFile,
    source_url: str | None = None,
    max_upload_size_bytes: int,
) -> StudyMaterial:
    _ensure_references_exist(db, course_id, uploaded_by)

    material = StudyMaterial(
        course_id=course_id,
        uploaded_by=uploaded_by,
        title=title,
        material_type=material_type,
        source_url=source_url,
    )
    db.add(material)
    db.flush()

    original_name = sanitize_filename(file.filename)
    ext = get_extension(original_name)

    destination = resolve_file_path(stored_filename_for(material.id, ext))
    try:
        size, mime_type = save_upload(
            file, destination, max_upload_size_bytes
        )
    except Exception:
        db.rollback()
        delete_stored_file(destination.name)
        raise

    material.file_name = original_name
    material.file_size = size
    material.mime_type = mime_type
    material.stored_file_name = destination.name
    material.status = "uploaded"

    try:
        db.commit()
        db.refresh(material)
    except Exception:
        db.rollback()
        delete_stored_file(destination.name)
        raise

    return material


def delete_study_material(db: Session, material_id: uuid.UUID, knowledge_base=None) -> None:
    material = get_study_material(db, material_id)
    stored_file_name = material.stored_file_name

    db.delete(material)
    db.commit()

    if stored_file_name:
        delete_stored_file(stored_file_name)

    _remove_rag_chunks(str(material_id), knowledge_base=knowledge_base)


def _remove_rag_chunks(
    material_id: str, knowledge_base=None
) -> None:
    """Best-effort removal of RAG chunks for a deleted material."""
    try:
        if knowledge_base is not None:
            knowledge_base.delete_material(material_id)
        else:
            from rag.knowledge_base import get_knowledge_base

            kb = get_knowledge_base()
            try:
                kb.delete_material(material_id)
            finally:
                kb.close()
    except Exception:
        logger.warning("Failed to remove RAG chunks for material %s", material_id)


def process_material(
    db: Session, material_id: uuid.UUID, knowledge_base=None
) -> StudyMaterial:
    """Process a study material: index it into the RAG knowledge base.

    Lifecycle: uploaded/failed -> processing -> processed | failed.
    Re-indexing the same material replaces prior chunks (idempotent).
    """
    material = get_study_material(db, material_id)
    material_id_str = str(material.id)

    material.status = "processing"
    material.processed_at = None
    material.error_message = None
    db.commit()
    db.refresh(material)

    if not material.stored_file_name:
        mark_material_failed(
            db, material_id, error_message="No stored file available for processing"
        )
        return get_study_material(db, material_id)

    try:
        path = resolve_file_path(material.stored_file_name)
    except ValueError:
        mark_material_failed(
            db, material_id, error_message="Stored file path is invalid"
        )
        return get_study_material(db, material_id)

    if not path.is_file():
        mark_material_failed(
            db, material_id, error_message="Stored file not found on disk"
        )
        return get_study_material(db, material_id)

    try:
        from rag.models import SourceRef

        source_ref = SourceRef(
            material_id=material_id_str,
            course_id=str(material.course_id),
            original_filename=material.file_name,
            material_title=material.title,
        )

        kb = knowledge_base
        owns_kb = False
        if kb is None:
            from rag.knowledge_base import get_knowledge_base

            kb = get_knowledge_base()
            owns_kb = True
        try:
            kb.index_material(
                str(path),
                source_ref=source_ref,
                uploaded_by=str(material.uploaded_by),
            )
        finally:
            if owns_kb:
                kb.close()

        return mark_material_processed(db, material_id)

    except Exception as exc:
        error_msg = str(exc)[:MAX_ERROR_MESSAGE_LENGTH]
        logger.exception("Processing failed for material %s", material_id_str)
        return mark_material_failed(db, material_id, error_message=error_msg)


# ---------------------------------------------------------------------------
# Processing lifecycle contract (no document processing is implemented).
#
# A future worker polls `list_materials_pending_processing` for new work and
# moves each material along the lifecycle with the `mark_material_*` helpers:
#
#     uploaded -> processing -> processed
#     uploaded/processing -> failed
#     failed -> processing (retry)
#
# These functions only mutate the database state; they never touch file
# contents or analysis logic.
# ---------------------------------------------------------------------------

MAX_ERROR_MESSAGE_LENGTH = 1000


def list_materials_pending_processing(
    db: Session, *, limit: int = 100
) -> list[StudyMaterial]:
    """Return newly uploaded materials that await processing.

    This is the polling contract for a future processing worker. It returns
    materials in ``uploaded`` state (the initial status), ordered oldest
    first, without touching any analysis logic.
    """
    query = (
        select(StudyMaterial)
        .where(StudyMaterial.status == "uploaded")
        .order_by(StudyMaterial.created_at)
        .limit(limit)
    )
    return list(db.scalars(query).all())


def mark_material_processing(db: Session, material_id: uuid.UUID) -> StudyMaterial:
    """Move a material into ``processing`` (start or retry)."""
    material = get_study_material(db, material_id)
    material.status = "processing"
    material.processed_at = None
    material.error_message = None
    db.commit()
    db.refresh(material)
    return material


def mark_material_processed(db: Session, material_id: uuid.UUID) -> StudyMaterial:
    """Record a successfully processed material."""
    material = get_study_material(db, material_id)
    material.status = "processed"
    material.processed_at = datetime.now(timezone.utc)
    material.error_message = None
    db.commit()
    db.refresh(material)
    return material


def mark_material_failed(
    db: Session, material_id: uuid.UUID, *, error_message: str
) -> StudyMaterial:
    """Record a processing failure with a safe, truncated message."""
    material = get_study_material(db, material_id)
    material.status = "failed"
    material.processed_at = None
    material.error_message = (error_message or "")[:MAX_ERROR_MESSAGE_LENGTH]
    db.commit()
    db.refresh(material)
    return material