"""PDF text extraction, page by page, using pypdf.

Visual detection is deliberately lightweight: it counts raster image XObjects
on each page by walking ``/Resources /XObject`` (recursing into Form
XObjects) WITHOUT decoding any pixels. A caption is lifted from the page text
when one exists. If pypdf's structure surprises us on a given page, that
page simply produces no visual element - text extraction is never affected.
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from rag.errors import CorruptDocumentError, ExtractionError, MissingFileError
from rag.extractors.base import Extractor
from rag.extractors.visuals import find_caption, guess_visual_type
from rag.models import (
    VISUAL_TYPE_UNKNOWN,
    ExtractedDocument,
    ExtractedSection,
    VisualElement,
)
from rag.normalize import normalize_text


def _count_page_image_xobjects(page) -> int:
    """Count raster image XObjects reachable from a page's resource tree.

    Never decodes pixel data; only inspects the content graph. Returns 0 on
    any structural surprise.
    """
    count = 0
    stack = [page]
    seen: set[int] = set()
    while stack:
        current = stack.pop()
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)
        try:
            resources = current.get("/Resources")
            if resources is None:
                continue
            xobjects = resources.get_object().get("/XObject")
            if xobjects is None:
                continue
            xobject_map = xobjects.get_object()
        except Exception:
            continue
        for name in xobject_map:
            try:
                target = xobject_map[name].get_object()
            except Exception:
                continue
            try:
                subtype = str(target.get("/Subtype", "") or "")
            except Exception:
                subtype = ""
            if subtype == "/Image":
                count += 1
            elif subtype == "/Form":
                stack.append(target)
    return count


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
        visuals: list[VisualElement] = []
        for page_number in range(len(reader.pages)):
            page = reader.pages[page_number]
            try:
                raw_text = page.extract_text() or ""
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

            try:
                if _count_page_image_xobjects(page) > 0:
                    caption = find_caption(text)
                    visuals.append(
                        VisualElement(
                            visual_id=f"p{page_number + 1}",
                            page=page_number + 1,
                            source_location=f"page {page_number + 1}",
                            visual_type=guess_visual_type(
                                caption, fallback=VISUAL_TYPE_UNKNOWN
                            ),
                            caption=caption,
                            nearby_text=text,
                        )
                    )
            except Exception:
                # Never fail page text extraction because of visual analysis.
                continue

        return ExtractedDocument(
            file_type=self.file_type,
            text="\n\n".join(
                section.text for section in sections if section.text
            ),
            sections=tuple(sections),
            visuals=tuple(visuals),
        )