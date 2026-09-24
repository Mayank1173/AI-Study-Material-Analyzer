"""Extractor tests: PDF, DOCX, PPTX, TXT plus corrupt/unsupported inputs."""

from __future__ import annotations

import pytest

from rag import extract_document
from rag.errors import (
    CorruptDocumentError,
    MissingFileError,
    UnsupportedFileTypeError,
)
from rag.extractors import (
    SUPPORTED_EXTRACTABLE_TYPES,
    get_extractor,
    normalize_file_type,
    supports_extension,
)
from rag.tests.sample_data import (
    DOCX_PARAGRAPH,
    PAGE_ONE_HEADING,
    PAGE_TWO_HEADING,
    SLIDE_ONE_LINES,
    SLIDE_TWO_LINES,
    SLIDE_TWO_NOTES,
    TXT_CONTENT,
)


def test_supported_extractable_types():
    assert SUPPORTED_EXTRACTABLE_TYPES == {".pdf", ".docx", ".pptx", ".txt"}


@pytest.mark.parametrize(
    "value,expected",
    [("pdf", ".pdf"), (".PDF", ".pdf"), (" docx ", ".docx"), ("", "")],
)
def test_normalize_file_type(value, expected):
    assert normalize_file_type(value) == expected


def test_supports_extension():
    assert supports_extension("pdf")
    assert not supports_extension(".png")


def test_get_extractor_rejects_unknown_type():
    with pytest.raises(UnsupportedFileTypeError):
        get_extractor(".png")


def test_pdf_extraction_page_by_page(pdf_path):
    document = extract_document(pdf_path)

    assert document.file_type == ".pdf"
    assert len(document.sections) == 2
    assert document.sections[0].page == 1
    assert document.sections[1].page == 2
    assert PAGE_ONE_HEADING in document.sections[0].text
    assert PAGE_TWO_HEADING in document.sections[1].text
    assert PAGE_TWO_HEADING not in document.sections[0].text
    assert PAGE_ONE_HEADING in document.text
    assert PAGE_TWO_HEADING in document.text


def test_docx_extraction_includes_paragraphs_and_tables(docx_path):
    document = extract_document(docx_path)

    assert document.file_type == ".docx"
    assert DOCX_PARAGRAPH in document.text
    assert "Third normal form" in document.text
    assert "1NF" in document.text
    assert "No transitive dependency" in document.text
    assert document.sections[0].page is None


def test_pptx_extraction_slide_by_slide(pptx_path):
    document = extract_document(pptx_path)

    assert document.file_type == ".pptx"
    assert len(document.sections) == 2
    assert document.sections[0].slide == 1
    assert document.sections[1].slide == 2
    assert "A process is a program in execution." in document.sections[0].text
    for line in SLIDE_TWO_LINES:
        assert line in document.sections[1].text
    assert SLIDE_TWO_NOTES in document.sections[1].text
    assert SLIDE_ONE_LINES[0] not in document.sections[1].text


def test_txt_extraction(txt_path):
    document = extract_document(txt_path)

    assert document.file_type == ".txt"
    assert TXT_CONTENT in document.text


def test_txt_falls_back_to_cp1252_for_non_utf8_bytes(tmp_path):
    path = tmp_path / "legacy.txt"
    path.write_bytes("café résumé naïve".encode("cp1252"))

    document = extract_document(path)
    assert "café" in document.text
    assert "résumé" in document.text


def test_file_type_can_be_overridden(tmp_path):
    path = tmp_path / "mystery.bin"
    path.write_text("plain content", encoding="utf-8")

    document = extract_document(path, file_type=".txt")
    assert "plain content" in document.text


def test_unsupported_extension_raises(unsupported_path):
    with pytest.raises(UnsupportedFileTypeError):
        extract_document(unsupported_path)


def test_missing_file_raises(tmp_path):
    with pytest.raises(MissingFileError):
        extract_document(tmp_path / "does-not-exist.txt")


def test_corrupt_pdf_raises(corrupt_pdf_path):
    with pytest.raises(CorruptDocumentError):
        extract_document(corrupt_pdf_path)


def test_corrupt_docx_raises(corrupt_docx_path):
    with pytest.raises(CorruptDocumentError):
        extract_document(corrupt_docx_path)


def test_corrupt_pptx_raises(corrupt_pptx_path):
    with pytest.raises(CorruptDocumentError):
        extract_document(corrupt_pptx_path)
