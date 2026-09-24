"""End-to-end pipeline tests: file -> extraction -> chunks + metadata."""

from __future__ import annotations

import uuid

import pytest

from rag import process_document
from rag.errors import (
    CorruptDocumentError,
    EmptyDocumentError,
    MissingFileError,
    UnsupportedFileTypeError,
)
from rag.models import SourceRef
from rag.tests.sample_data import TXT_CONTENT


def make_source_ref(**overrides) -> SourceRef:
    defaults = dict(
        material_id=str(uuid.uuid4()),
        course_id=str(uuid.uuid4()),
        original_filename="reading.txt",
        material_title="Chapter notes",
        source_type=".txt",
    )
    defaults.update(overrides)
    return SourceRef(**defaults)


def test_short_txt_produces_single_metadata_rich_chunk(txt_path):
    result = process_document(txt_path, source_ref=make_source_ref())

    assert result.total_chunks == 1
    assert len(result.chunks) == 1
    assert result.file_type == ".txt"
    assert TXT_CONTENT in result.extracted_text

    metadata = result.chunks[0].metadata
    assert metadata.material_id is not None
    assert metadata.course_id is not None
    assert metadata.original_filename == "reading.txt"
    assert metadata.material_title == "Chapter notes"
    assert metadata.source_type == ".txt"
    assert metadata.chunk_index == 0
    assert metadata.total_chunks == 1


def test_pdf_chunks_carry_page_numbers(pdf_path):
    source_ref = make_source_ref(
        original_filename="lecture.pdf", source_type=".pdf"
    )
    result = process_document(
        pdf_path, source_ref=source_ref, chunk_size=60, overlap=0
    )

    assert result.total_chunks > 1
    for chunk in result.chunks:
        assert chunk.text.strip()
        assert chunk.metadata.page in (1, 2)
        assert chunk.metadata.slide is None

    assert result.chunks[0].metadata.page == 1
    pages = {chunk.metadata.page for chunk in result.chunks}
    assert pages == {1, 2}


def test_pptx_chunks_carry_slide_numbers(pptx_path):
    source_ref = make_source_ref(
        original_filename="slides.pptx", source_type=".pptx"
    )
    result = process_document(
        pptx_path, source_ref=source_ref, chunk_size=60, overlap=0
    )

    assert result.total_chunks > 1
    slides = {chunk.metadata.slide for chunk in result.chunks}
    assert slides == {1, 2}
    assert all(chunk.metadata.page is None for chunk in result.chunks)


def test_chunk_indices_are_sequential_and_deterministic(pdf_path):
    source_ref = make_source_ref(
        original_filename="lecture.pdf", source_type=".pdf"
    )
    first = process_document(
        pdf_path, source_ref=source_ref, chunk_size=60, overlap=15
    )
    second = process_document(
        pdf_path, source_ref=source_ref, chunk_size=60, overlap=15
    )

    assert len(first.chunks) == first.total_chunks == len(second.chunks)
    assert [c.metadata.chunk_index for c in first.chunks] == list(
        range(first.total_chunks)
    )
    assert [c.text for c in first.chunks] == [c.text for c in second.chunks]
    assert [c.metadata for c in first.chunks] == [c.metadata for c in second.chunks]


def test_source_type_inferred_from_original_filename(tmp_path):
    path = tmp_path / "content.bin"
    path.write_text("Opaque extension but real text inside.", encoding="utf-8")

    result = process_document(
        path,
        source_ref=make_source_ref(
            original_filename="notes.txt", source_type=None
        ),
    )
    assert result.file_type == ".txt"
    assert result.chunks[0].metadata.source_type == ".txt"


def test_file_type_parameter_overrides_metadata(tmp_path):
    path = tmp_path / "content.txt"
    path.write_text("Explicit override wins.", encoding="utf-8")

    result = process_document(
        path, source_ref=make_source_ref(), file_type="txt"
    )
    assert result.file_type == ".txt"


def test_empty_txt_raises(empty_txt_path):
    with pytest.raises(EmptyDocumentError):
        process_document(empty_txt_path, source_ref=make_source_ref())


def test_empty_pdf_raises(empty_pdf_path):
    with pytest.raises(EmptyDocumentError):
        process_document(empty_pdf_path, source_ref=make_source_ref())


def test_unsupported_type_raises(unsupported_path):
    source_ref = SourceRef(
        material_id=str(uuid.uuid4()),
        course_id=str(uuid.uuid4()),
        original_filename="legacy.doc",
        source_type=None,
    )
    with pytest.raises(UnsupportedFileTypeError):
        process_document(unsupported_path, source_ref=source_ref)


def test_corrupt_pdf_raises(corrupt_pdf_path):
    with pytest.raises(CorruptDocumentError):
        process_document(corrupt_pdf_path, source_ref=make_source_ref())


def test_corrupt_docx_raises(corrupt_docx_path):
    with pytest.raises(CorruptDocumentError):
        process_document(corrupt_docx_path, source_ref=make_source_ref())


def test_missing_file_raises(tmp_path):
    with pytest.raises(MissingFileError):
        process_document(
            tmp_path / "ghost.txt", source_ref=make_source_ref()
        )