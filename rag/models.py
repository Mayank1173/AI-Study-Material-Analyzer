"""Internal data structures for the RAG document-processing pipeline.

The RAG layer never duplicates the full PostgreSQL ``StudyMaterial`` record.
Instead it keeps lightweight references (IDs, titles, filenames) that let a
future indexing stage trace every chunk back to its source row in the backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceRef:
    """References connecting processed content back to the backend record.

    ``material_id`` and ``course_id`` are the foreign keys into PostgreSQL;
    they are stored as opaque strings so the RAG layer stays database-agnostic.
    ``source_type`` is the normalized file extension (e.g. ``".pdf"``).
    """

    material_id: str | None = None
    course_id: str | None = None
    original_filename: str | None = None
    material_title: str | None = None
    source_type: str | None = None
    source_location: str | None = None


@dataclass(frozen=True)
class ExtractedSection:
    """One addressable fragment of a document (a PDF page, a slide, ...).

    ``page`` and ``slide`` are mutually exclusive: exactly one is populated
    depending on the source format. ``source_location`` is an optional free-form
    human-readable pointer (e.g. ``"Slide 3"`` or ``"Appendix A"``).
    """

    text: str
    page: int | None = None
    slide: int | None = None
    source_location: str | None = None


@dataclass(frozen=True)
class ExtractedDocument:
    """Raw, normalized text produced by a single extractor."""

    file_type: str
    text: str = ""
    sections: tuple[ExtractedSection, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ChunkMetadata:
    """Metadata attached to one chunk, sufficient to trace it to its source."""

    material_id: str | None = None
    course_id: str | None = None
    original_filename: str | None = None
    material_title: str | None = None
    source_type: str | None = None
    chunk_index: int = 0
    total_chunks: int = 0
    page: int | None = None
    slide: int | None = None
    source_location: str | None = None

    @classmethod
    def for_chunk(
        cls,
        source: SourceRef,
        *,
        chunk_index: int,
        total_chunks: int,
        page: int | None = None,
        slide: int | None = None,
        source_location: str | None = None,
    ) -> "ChunkMetadata":
        return cls(
            material_id=source.material_id,
            course_id=source.course_id,
            original_filename=source.original_filename,
            material_title=source.material_title,
            source_type=source.source_type,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            page=page,
            slide=slide,
            source_location=source_location,
        )


@dataclass(frozen=True)
class TextChunk:
    """A single ready-to-embed document fragment plus its metadata."""

    text: str
    metadata: ChunkMetadata


@dataclass(frozen=True)
class ProcessedDocument:
    """The full output of the Phase 1 pipeline for one source document."""

    source: SourceRef
    file_type: str
    extracted_text: str
    chunks: tuple[TextChunk, ...]
    total_chunks: int


@dataclass(frozen=True)
class IndexedChunk:
    """A chunk plus its fixed-size embedding vector, ready to persist.

    ``chunk_id`` is ``"{material_id}:{chunk_index}"`` and uniquely identifies a
    chunk inside a material's index. ``embedding`` is a ``tuple[float,...]`` of
    length ``embedder.dimension``.
    """

    chunk_id: str
    material_id: str
    course_id: str
    uploaded_by: str
    text: str
    embedding: tuple[float, ...]
    metadata: ChunkMetadata

    @classmethod
    def from_text_chunk(
        cls,
        chunk: TextChunk,
        *,
        chunk_id: str,
        material_id: str,
        course_id: str,
        uploaded_by: str,
        embedding: tuple[float, ...],
    ) -> "IndexedChunk":
        if not material_id:
            raise ValueError("material_id must be a non-empty string")
        if not uploaded_by:
            raise ValueError("uploaded_by must be a non-empty string")
        return cls(
            chunk_id=chunk_id,
            material_id=material_id,
            course_id=course_id,
            uploaded_by=uploaded_by,
            text=chunk.text,
            embedding=embedding,
            metadata=chunk.metadata,
        )


@dataclass(frozen=True)
class SearchResult:
    """One vector-store hit: the chunk text plus its cosine similarity score."""

    chunk_id: str
    material_id: str
    course_id: str
    uploaded_by: str
    text: str
    score: float
    metadata: ChunkMetadata