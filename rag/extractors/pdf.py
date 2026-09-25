"""PDF text extraction, page by page, using pypdf."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from rag.errors import CorruptDocumentError, ExtractionError, MissingFileError
from rag.extractors.base import Extractor
from rag.models import ExtractedDocument, ExtractedSection
from rag.normalize import normalize_text


class PdfExtractor(Extractor):
    file_type = ".pdf"

    def extract(self, source: str | Path) -> ExtractedDocument:
        path = self.resolve_path(source)
        try:
            reader = PdfReader(str(path), strict=False)
        except PyPdfError as exc:
            raise CorruptDocumentError(
                "The PDF document is corrupt or malformed"
            ) from exc
        except OSError as exc:
            raise MissingFileError("The source document could not be read") from exc

        if getattr(reader, "is_encrypted", False):
            raise ExtractionError(
                "The PDF document is encrypted and cannot be read"
            )

        sections: list[ExtractedSection] = []
        for page_number in range(len(reader.pages)):
            try:
                raw_text = reader.pages[page_number].extract_text() or ""
            except (PyPdfError, ValueError):
                raw_text = ""
            text = normalize_text(raw_text)
            sections.append(
                ExtractedSection(
                    text=text,
                    page=page_number + 1,
                    source_location=f"page {page_number + 1}",
                )
            )

        return ExtractedDocument(
            file_type=self.file_type,
            text="\n\n".join(
                section.text for section in sections if section.text
            ),
            sections=tuple(sections),
        )