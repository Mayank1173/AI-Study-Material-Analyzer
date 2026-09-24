"""Phase 1 document-processing pipeline.

    file -> extraction -> normalization -> chunking -> chunks + metadata

The pipeline is deliberately independent of FastAPI and the database: it takes
a local file path plus a :class:`SourceRef` (IDs referencing the backend's
``StudyMaterial`` row) and returns a :class:`ProcessedDocument` ready for a
future embedding/indexing stage.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from rag.chunking import TextChunker
from rag.errors import EmptyDocumentError, MissingFileError
from rag.extraction import extract_document
from rag.extractors import normalize_file_type, supports_extension
from rag.models import (
    ChunkMetadata,
    ExtractedSection,
    ProcessedDocument,
    SourceRef,
    TextChunk,
    VisualElement,
)
from rag.normalize import normalize_text

_JOINER = "\n\n"
SectionInterval = tuple[int, int, ExtractedSection]


def _materialize_visual(visual: VisualElement, ref: SourceRef) -> VisualElement:
    """Attach the source-record references to one extracted visual element."""
    material_id = ref.material_id
    return VisualElement(
        visual_id=f"{material_id}:{visual.visual_id}" if material_id else visual.visual_id,
        material_id=material_id,
        course_id=ref.course_id,
        original_filename=ref.original_filename,
        material_title=ref.material_title,
        page=visual.page,
        slide=visual.slide,
        source_location=visual.source_location,
        visual_type=visual.visual_type,
        caption=visual.caption,
        nearby_text=visual.nearby_text,
        description=visual.description,
        pixel_analyzed=visual.pixel_analyzed,
    )


def _extension_of(filename: str | None) -> str:
    return normalize_file_type(Path(filename).suffix) if filename else ""


def _resolve_file_type(
    file_type: str | None, source: str, ref: SourceRef
) -> str:
    """Pick the file type to extract with.

    Precedence: an explicit ``file_type`` argument, then the stored file's own
    extension (validated at upload time by the backend), then the references.
    The first candidate with a registered extractor wins; the first non-empty
    candidate is returned (and rejected by the extractor registry) when none of
    them are extractable.
    """
    candidates = (
        normalize_file_type(file_type),
        _extension_of(str(source)),
        normalize_file_type(ref.source_type),
        _extension_of(ref.original_filename),
    )
    for candidate in candidates:
        if candidate and supports_extension(candidate):
            return candidate
    return next((candidate for candidate in candidates if candidate), "")


def _assemble(sections: tuple[ExtractedSection, ...]) -> tuple[str, list[SectionInterval]]:
    """Join normalized section texts and record each section's char range."""
    parts: list[str] = []
    intervals: list[SectionInterval] = []
    offset = 0

    for section in sections:
        text = normalize_text(section.text)
        if text:
            if parts:
                offset += len(_JOINER)
            start = offset
            parts.append(text)
            offset += len(text)
            end = offset
        else:
            start = end = offset
        intervals.append((start, end, section))

    return _JOINER.join(parts), intervals


def _locate(
    intervals: list[SectionInterval], offset: int
) -> tuple[int | None, int | None, str | None]:
    """Find the section covering ``offset`` and return its location fields."""
    if not intervals:
        return None, None, None

    best: SectionInterval | None = None
    for interval in intervals:
        start, _end, section = interval
        if start > offset:
            break
        if best is None or start > best[0] or (
            start == best[0] and not best[2].text and section.text
        ):
            best = interval

    if best is None:
        best = intervals[0]

    section = best[2]
    return section.page, section.slide, section.source_location


def process_document(
    source: str | Path,
    *,
    source_ref: SourceRef | None = None,
    file_type: str | None = None,
    chunk_size: int = 1500,
    overlap: int = 150,
) -> ProcessedDocument:
    """Run the full Phase 1 pipeline for a single document.

    Args:
        source: local path to the stored document.
        source_ref: references (material/subject IDs, title, filename) that let
            every chunk be traced back to the backend's ``StudyMaterial`` row.
        file_type: optional extension override (with or without a dot); when
            omitted it is taken from ``source_ref.source_type`` or the filename.
        chunk_size: maximum characters per chunk.
        overlap: characters of context carried from one chunk into the next.
    """
    ref = source_ref or SourceRef()

    path = Path(source)
    if not path.exists():
        raise MissingFileError("The source document does not exist")
    if not path.is_file():
        raise MissingFileError("The source is not a regular file")

    resolved_type = _resolve_file_type(file_type, str(source), ref)

    extracted = extract_document(path, file_type=resolved_type)
    combined, intervals = _assemble(extracted.sections)
    if not combined:
        raise EmptyDocumentError("The document contains no extractable text")

    ref = replace(ref, source_type=resolved_type)

    chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
    ranges = chunker.split_ranges(combined)
    if not ranges:
        raise EmptyDocumentError("The document contains no extractable text")

    total = len(ranges)
    chunks: list[TextChunk] = []
    for index, rng in enumerate(ranges):
        page, slide, location = _locate(intervals, rng.offset)
        metadata = ChunkMetadata.for_chunk(
            ref,
            chunk_index=index,
            total_chunks=total,
            page=page,
            slide=slide,
            source_location=location,
        )
        chunks.append(TextChunk(text=rng.text, metadata=metadata))

    visuals = tuple(_materialize_visual(v, ref) for v in extracted.visuals)

    return ProcessedDocument(
        source=ref,
        file_type=resolved_type,
        extracted_text=combined,
        chunks=tuple(chunks),
        total_chunks=total,
        visuals=visuals,
    )