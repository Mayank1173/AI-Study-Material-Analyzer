"""Unit tests for the TextChunker."""

from __future__ import annotations

import pytest

from rag.chunking import TextChunker
from rag.normalize import normalize_text


def shared_suffix_prefix(first: str, second: str) -> int:
    """Length of the longest suffix of ``first`` equal to a prefix of ``second``."""
    limit = min(len(first), len(second))
    for size in range(limit, 0, -1):
        if first[-size:] == second[:size]:
            return size
    return 0


def test_empty_text_yields_no_chunks():
    assert TextChunker().split("") == []
    assert TextChunker().split("   \n\n  \t\n") == []


def test_short_text_is_a_single_chunk():
    chunker = TextChunker(chunk_size=1000, overlap=0)
    assert chunker.split("Just a small paragraph of text.") == [
        "Just a small paragraph of text."
    ]


def test_chunks_respect_size_limit():
    text = (
        "Every chunk must stay within the configured character budget. "
        "This ensures embedding calls stay predictable and cheap. "
        "We repeat enough content to force several chunk boundaries. "
        "Long documents are split into smaller, indexable fragments. "
        "Each fragment keeps its own metadata for provenance."
    ) * 4
    chunker = TextChunker(chunk_size=100, overlap=0)
    chunks = chunker.split(text)

    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_chunks_preserve_paragraph_order():
    text = (
        "Alpha paragraph one.\n\n"
        "Beta paragraph two.\n\n"
        "Gamma paragraph three."
    )
    chunks = TextChunker(chunk_size=30, overlap=0).split(text)
    assert "\n\n".join(chunks) == text


def test_paragraph_boundaries_are_respected():
    paragraph_one = "Paragraph one has exactly enough words to fill one chunk."
    paragraph_two = "Paragraph two is a completely separate block of content."
    chunker = TextChunker(chunk_size=62, overlap=0)
    chunks = chunker.split(f"{paragraph_one}\n\n{paragraph_two}")

    assert len(chunks) == 2
    assert chunks[0] == paragraph_one
    assert chunks[1] == paragraph_two


def test_long_paragraph_is_split_not_truncated():
    sentence = "The quick brown fox jumps over the lazy dog while learning. "
    text = sentence * 20
    chunks = TextChunker(chunk_size=100, overlap=0).split(text)

    assert len(chunks) >= 2
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert all(chunk.strip() for chunk in chunks)


def test_overlap_carries_context_between_chunks():
    text = (
        "The mitochondria is the powerhouse of the cell. "
        "ATP is produced during oxidative phosphorylation. "
        "Electrons move along the electron transport chain. "
        "The proton gradient powers ATP synthase. "
        "Substrate-level phosphorylation also yields ATP."
    )
    chunker = TextChunker(chunk_size=120, overlap=20)
    chunks = chunker.split(text)

    assert len(chunks) > 1
    for first, second in zip(chunks, chunks[1:]):
        overlap = shared_suffix_prefix(first, second)
        assert overlap > 0
        assert overlap <= 20
    assert all(len(chunk) <= 120 for chunk in chunks)


def test_overlap_is_capped_when_next_chunk_has_no_headroom():
    text = (
        "A paragraph that exactly consumes its budget leaves no headroom "
        "for overlap before the next chunk begins with its own content."
    )
    chunks = TextChunker(chunk_size=60, overlap=20).split(text)

    assert all(len(chunk) <= 60 for chunk in chunks)
    assert all(chunk.strip() for chunk in chunks)


def test_no_overlap_when_overlap_is_zero():
    text = (
        "First idea about chemical bonds. "
        "Second idea about molecular geometry. "
        "Third idea about intermolecular forces. "
        "Fourth paragraph stays far apart from the fifth topic."
    )
    chunks = TextChunker(chunk_size=45, overlap=0).split(text)

    for first, second in zip(chunks, chunks[1:]):
        assert shared_suffix_prefix(first, second) == 0


def test_deterministic_ordering():
    text = (
        "Determinism matters for search and caching. "
        "The same input must always produce identical chunks. "
        "Ordering is stable because chunking never touches randomness. "
        "Repeated calls return byte-for-byte equal results."
    ) * 3
    chunker = TextChunker(chunk_size=80, overlap=10)

    assert chunker.split(text) == chunker.split(text)


def test_normalize_text_is_idempotent_and_clean():
    raw = "  Line one  \r\nLine two\r\n\r\n\r\n   Line three\t\r"
    once = normalize_text(raw)
    assert once == "Line one\nLine two\n\nLine three"
    assert normalize_text(once) == once


def test_normalize_removes_stray_control_characters():
    raw = "Hello\x00 world\x07 binary\x1f values"
    assert normalize_text(raw) == "Hello world binary values"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"chunk_size": 0},
        {"chunk_size": -5},
        {"overlap": -1},
        {"chunk_size": 10, "overlap": 10},
        {"chunk_size": 10, "overlap": 15},
    ],
)
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        TextChunker(**kwargs)