import re
from pathlib import PurePosixPath, PureWindowsPath

from app.services.errors import UnsupportedFileTypeError

ALLOWED_FILE_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    },
    ".pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    },
    ".txt": {"text/plain", "text/plain; charset=utf-8"},
}

_FORBIDDEN_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_filename(filename: str | None) -> str:
    if not filename:
        raise UnsupportedFileTypeError("No filename was provided")

    cleaned = filename.replace("\\", "/")
    cleaned = cleaned.rstrip("/")

    posix = PurePosixPath(cleaned).name
    windows = PureWindowsPath(cleaned).name
    name = posix or windows

    name = _FORBIDDEN_CHARS.sub("", name).strip().lstrip(".")
    if not name or name in {".", ".."}:
        raise UnsupportedFileTypeError("No filename was provided")

    return name


def get_extension(filename: str) -> str:
    index = filename.rfind(".")
    if index <= 0:
        return ""
    return filename[index:].lower()


def validate_extension(filename: str) -> str:
    ext = get_extension(filename)
    if ext not in ALLOWED_FILE_TYPES:
        raise UnsupportedFileTypeError(
            f"File type '{ext or 'unknown'}' is not supported"
        )
    return ext


def resolve_content_type(ext: str, declared: str | None) -> str:
    allowed = ALLOWED_FILE_TYPES[ext]
    canonical = sorted(allowed)[0]

    if declared and declared.split(";")[0].strip().lower() in allowed:
        return declared.strip()

    return canonical