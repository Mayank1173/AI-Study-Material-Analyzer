"""PPTX text extraction using python-pptx, slide by slide.

Every slide becomes one addressable section carrying its slide number so chunk
metadata can point back to the exact slide the text came from. Speaker notes
are included when present because they often carry the slide's talking points.

Visual detection walks each slide's shapes looking for pictures and chart
graphic frames (never decoding image bytes). The slide's first text line is
used as the caption and the slide's full text as surrounding context.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.exc import PackageNotFoundError

from rag.errors import CorruptDocumentError, MissingFileError
from rag.extractors.base import Extractor
from rag.extractors.visuals import guess_visual_type
from rag.models import (
    VISUAL_TYPE_CHART,
    VISUAL_TYPE_IMAGE,
    VISUAL_TYPE_UNKNOWN,
    ExtractedDocument,
    ExtractedSection,
    VisualElement,
)
from rag.normalize import normalize_text


class PptxExtractor(Extractor):
    file_type = ".pptx"

    def extract(self, source: str | Path) -> ExtractedDocument:
        path = self.resolve_path(source)
        try:
            presentation = Presentation(str(path))
        except (PackageNotFoundError, zipfile.BadZipFile) as exc:
            raise CorruptDocumentError(
                "The PPTX document is corrupt or not a valid PowerPoint file"
            ) from exc
        except OSError as exc:
            raise MissingFileError("The source document could not be read") from exc

        sections: list[ExtractedSection] = []
        visuals: list[VisualElement] = []
        for index, slide in enumerate(presentation.slides, start=1):
            lines = self._slide_text(slide)
            text = normalize_text("\n".join(lines))
            sections.append(
                ExtractedSection(
                    text=text,
                    slide=index,
                    source_location=f"slide {index}",
                )
            )

            visual = self._detect_visual(slide, index)
            if visual is not None:
                visuals.append(visual)

        return ExtractedDocument(
            file_type=self.file_type,
            text="\n\n".join(
                section.text for section in sections if section.text
            ),
            sections=tuple(sections),
            visuals=tuple(visuals),
        )

    @staticmethod
    def _slide_text(slide) -> list[str]:
        lines: list[str] = []
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            for paragraph in shape.text_frame.paragraphs:
                content = "".join(run.text for run in paragraph.runs).strip()
                if content:
                    lines.append(content)

        try:
            notes = slide.notes_slide.notes_text_frame.text
        except (KeyError, ValueError, AttributeError):
            notes = ""
        if notes and notes.strip():
            lines.append(f"[notes] {notes.strip()}")
        return lines

    @staticmethod
    def _shape_is_picture(shape) -> bool:
        try:
            return (
                getattr(shape, "shape_type", None) == MSO_SHAPE_TYPE.PICTURE
                and getattr(shape, "image", None) is not None
            )
        except Exception:
            return False

    @classmethod
    def _find_picture(cls, shapes) -> bool:
        for shape in shapes:
            try:
                if cls._shape_is_picture(shape):
                    return True
                if getattr(shape, "shape_type", None) == MSO_SHAPE_TYPE.GROUP:
                    if cls._find_picture(shape.shapes):
                        return True
            except Exception:
                continue
        return False

    @classmethod
    def _find_chart(cls, shapes) -> bool:
        for shape in shapes:
            try:
                if getattr(shape, "has_chart", False):
                    return True
                if getattr(shape, "shape_type", None) == MSO_SHAPE_TYPE.GROUP:
                    if cls._find_chart(shape.shapes):
                        return True
            except Exception:
                continue
        return False

    @classmethod
    def _detect_visual(cls, slide, slide_number: int) -> VisualElement | None:
        try:
            lines = [
                line for line in cls._slide_text(slide) if not line.startswith("[notes]")
            ]
            text = "\n".join(lines)
            caption = normalize_text(lines[0]) if lines else ""

            has_picture = cls._find_picture(slide.shapes)
            has_chart = cls._find_chart(slide.shapes)
            if not has_picture and not has_chart:
                return None

            visual_type = VISUAL_TYPE_UNKNOWN
            if has_chart and not has_picture:
                visual_type = VISUAL_TYPE_CHART
            elif has_picture:
                visual_type = guess_visual_type(caption, fallback=VISUAL_TYPE_IMAGE)

            return VisualElement(
                visual_id=f"s{slide_number}",
                slide=slide_number,
                source_location=f"slide {slide_number}",
                visual_type=visual_type,
                caption=caption,
                nearby_text=normalize_text(text),
            )
        except Exception:
            # Never fail slide text extraction because of visual analysis.
            return None