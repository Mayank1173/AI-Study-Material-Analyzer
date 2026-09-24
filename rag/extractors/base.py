"""Base contract for document extractors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from rag.errors import ExtractionError, MissingFileError
from rag.models import ExtractedDocument


class Extractor(ABC):
    """Extract normalized text from a single document format.

    Implementations accept a local file path (``str | Path``) and return an
    :class:`ExtractedDocument`. Low-level parsing failures must be translated
    into the controlled :mod:`rag.errors` hierarchy.
    """

    file_type: str = ""

    def __init__(self) -> None:
        if not self.file_type:
            raise TypeError(f"{type(self).__name__} must define file_type")

    @abstractmethod
    def extract(self, source: str | Path) -> ExtractedDocument:
        """Extract text from the document at ``source``."""

    @staticmethod
    def resolve_path(source: str | Path) -> Path:
        path = Path(source)
        if not path.exists():
            raise MissingFileError("The source document does not exist")
        if not path.is_file():
            raise ExtractionError("The source is not a regular file")
        return path