"""Extractor registry: maps normalized file extensions to extractor classes.

Extraction is intentionally a superset-free, whitelisted set: only formats
with a battle-tested extractor appear here. Formats the backend accepts but
Phase 1 cannot extract yet (``.ppt``, ``.doc``, images) are deliberately absent
and raise :class:`UnsupportedFileTypeError` when the pipeline requests them.
"""

from __future__ import annotations

from rag.errors import UnsupportedFileTypeError
from rag.extractors.base import Extractor
from rag.extractors.docx import DocxExtractor
from rag.extractors.pdf import PdfExtractor
from rag.extractors.pptx import PptxExtractor
from rag.extractors.txt import TxtExtractor

EXTRACTORS: dict[str, type[Extractor]] = {
    extractor.file_type: extractor
    for extractor in (
        PdfExtractor,
        DocxExtractor,
        PptxExtractor,
        TxtExtractor,
    )
}

SUPPORTED_EXTRACTABLE_TYPES = frozenset(EXTRACTORS)


def normalize_file_type(file_type: str | None) -> str:
    """Normalize a file type to a leading-dot lowercase extension."""
    value = (file_type or "").strip().lower()
    if not value:
        return ""
    if not value.startswith("."):
        value = f".{value}"
    return value


def supports_extension(file_type: str | None) -> bool:
    return normalize_file_type(file_type) in EXTRACTORS


def get_extractor(file_type: str | None) -> Extractor:
    normalized = normalize_file_type(file_type)
    if normalized not in EXTRACTORS:
        raise UnsupportedFileTypeError(
            f"File type '{normalized or 'unknown'}' is not supported for "
            "text extraction"
        )
    return EXTRACTORS[normalized]()