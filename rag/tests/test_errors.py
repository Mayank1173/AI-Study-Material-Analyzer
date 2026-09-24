"""Guarantees about error behavior: controlled types and no path leakage.

User-facing messages must never expose absolute filesystem paths, so the tests
assert that the sanitized message text (not just the exception class) stays
free of any path prefix.
"""

from __future__ import annotations

import pytest

from rag import process_document
from rag.errors import (
    CorruptDocumentError,
    EmptyDocumentError,
    MissingFileError,
    RagError,
    UnsupportedFileTypeError,
)
from rag.models import SourceRef


def assert_safe_message(exc: Exception, tmp_path) -> None:
    message = str(exc)
    assert str(tmp_path) not in message
    assert "\\" not in message.replace("-", "").replace(".", "").replace("/", "")
    assert not message or message.strip()


@pytest.mark.parametrize(
    "path_fixture,expected",
    [
        ("corrupt_pdf_path", CorruptDocumentError),
        ("corrupt_docx_path", CorruptDocumentError),
        ("corrupt_pptx_path", CorruptDocumentError),
        ("unsupported_path", UnsupportedFileTypeError),
    ],
)
def test_processing_errors_are_controlled_and_safe(
    request, path_fixture, expected, tmp_path
):
    source = request.getfixturevalue(path_fixture)
    with pytest.raises(expected) as exc_info:
        process_document(
            source,
            source_ref=SourceRef(
                material_id="m-1",
                original_filename=source.name,
                source_type=None,
            ),
        )
    assert_safe_message(exc_info.value, tmp_path)
    assert isinstance(exc_info.value, RagError)


def test_missing_file_error_is_safe(tmp_path):
    with pytest.raises(MissingFileError) as exc_info:
        process_document(
            tmp_path / "nope.txt",
            source_ref=SourceRef(
                material_id="m-1",
                original_filename="nope.txt",
                source_type=".txt",
            ),
        )
    assert_safe_message(exc_info.value, tmp_path)


def test_empty_document_error_is_safe(empty_txt_path, tmp_path):
    with pytest.raises(EmptyDocumentError) as exc_info:
        process_document(
            empty_txt_path, source_ref=SourceRef(source_type=".txt")
        )
    assert_safe_message(exc_info.value, tmp_path)


def test_extraction_error_messages_do_not_include_absolute_path(corrupt_pdf_path):
    with pytest.raises(CorruptDocumentError) as exc_info:
        process_document(
            corrupt_pdf_path, source_ref=SourceRef(source_type=".pdf")
        )
    message = str(exc_info.value)
    assert str(corrupt_pdf_path) not in message
    assert not message.startswith("C:")


def test_docx_source_type_mismatch_is_detected(tmp_path):
    """A .pdf label on a text file must not silently extract as text."""
    path = tmp_path / "fake.pdf"
    path.write_text("Plain text pretending to be a PDF.", encoding="utf-8")
    with pytest.raises(CorruptDocumentError):
        process_document(path, source_ref=SourceRef(source_type=".pdf"))