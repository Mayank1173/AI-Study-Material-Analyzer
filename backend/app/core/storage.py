import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.file_security import resolve_content_type, validate_extension
from app.services.errors import FileTooLargeError

_CHUNK_SIZE = 1024 * 1024


def get_storage_dir() -> Path:
    storage_dir = get_settings().storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def stored_filename_for(material_id: uuid.UUID, ext: str) -> str:
    return f"{material_id}{ext}"


def resolve_file_path(stored_file_name: str) -> Path:
    name = Path(stored_file_name)
    if name.is_absolute() or name.drive:
        raise ValueError("absolute paths are not allowed")

    root = get_storage_dir().resolve()
    candidate = (root / name).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("path escapes the storage directory")

    return candidate


def save_upload(
    file: UploadFile, destination: Path, max_bytes: int
) -> tuple[int, str]:
    ext = validate_extension(file.filename or "")
    mime_type = resolve_content_type(ext, file.content_type)

    total = 0
    with destination.open("wb") as handle:
        while True:
            chunk = file.file.read(_CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise FileTooLargeError(
                    f"File exceeds the maximum allowed size of {max_bytes} bytes"
                )
            handle.write(chunk)

    return total, mime_type


def delete_stored_file(stored_file_name: str) -> None:
    try:
        path = resolve_file_path(stored_file_name)
        path.unlink(missing_ok=True)
    except (ValueError, OSError):
        pass