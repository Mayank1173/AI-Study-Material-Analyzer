"""Plain-text extractor with encoding tolerance."""

from __future__ import annotations

from pathlib import Path

from rag.errors import CorruptDocumentError, ExtractionError, MissingFileError
from rag.extractors.base import Extractor
from rag.models import ExtractedDocument, ExtractedSection
from rag.normalize import normalize_text

_DECODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


class TxtExtractor(Extractor):
    file_type = ".txt"

    def extract(self, source: str | Path) -> ExtractedDocument:
        path = self.resolve_path(source)
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise MissingFileError("The source document could not be read") from exc

        text = self._decode(raw)
        return ExtractedDocument(
            file_type=self.file_type,
            text=normalize_text(text),
            sections=(ExtractedSection(text=normalize_text(text)),),
        )

    @staticmethod
    def _decode(raw: bytes) -> str:
        if not raw:
            return ""
        for encoding in _DECODINGS:
            try:
                return raw.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        raise CorruptDocumentError(
            "The text file uses an unsupported encoding"
        )