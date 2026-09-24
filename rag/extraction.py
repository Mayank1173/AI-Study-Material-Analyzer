"""High-level document extraction dispatch.

Picks the right extractor for a file and wraps every low-level failure into the
controlled ``rag.errors`` hierarchy. Messages are sanitized: they never expose
the absolute source path or internal storage details.
"""

from __future__ import annotations

from pathlib import Path

from rag.errors import ExtractionError, RagError
from rag.extractors import get_extractor, normalize_file_type
from rag.models import ExtractedDocument


def _extension_of(filename: str | None) -> str:
    if not filename:
        return ""
    return normalize_file_type(Path(filename).suffix)


def extract_document(
    source: str | Path,
    *,
    file_type: str | None = None,
) -> ExtractedDocument:
    """Extract normalized text from a local document file.

    ``file_type`` is the extension (with or without the leading dot). When
    omitted it is inferred from the source filename suffix.
    """
    resolved_type = normalize_file_type(file_type) or _extension_of(
        str(source)
    )
    extractor = get_extractor(resolved_type)

    try:
        return extractor.extract(source)
    except RagError:
        raise
    except Exception as exc:
        raise ExtractionError(
            "Unexpected error while extracting the document"
        ) from exc