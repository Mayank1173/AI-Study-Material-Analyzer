"""DOCX text extraction using python-docx.

python-docx has no reliable page-layout information, so extracted sections
carry no page numbers. Paragraph and table text are both included because table
content is often where key facts live.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from rag.errors import CorruptDocumentError, MissingFileError
from rag.extractors.base import Extractor
from rag.models import ExtractedDocument, ExtractedSection
from rag.normalize import normalize_text


class DocxExtractor(Extractor):
    file_type = ".docx"

    def extract(self, source: str | Path) -> ExtractedDocument:
        path = self.resolve_path(source)
        try:
            document = Document(str(path))
        except (PackageNotFoundError, zipfile.BadZipFile) as exc:
            raise CorruptDocumentError(
                "The DOCX document is corrupt or not a valid Word file"
            ) from exc
        except OSError as exc:
            raise MissingFileError("The source document could not be read") from exc

        parts: list[str] = []

        for paragraph in document.paragraphs:
            if paragraph.text and paragraph.text.strip():
                parts.append(paragraph.text.strip())

        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))

        text = normalize_text("\n".join(parts))
        return ExtractedDocument(
            file_type=self.file_type,
            text=text,
            sections=(ExtractedSection(text=text),),
        )