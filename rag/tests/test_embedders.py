"""Tests for the embedder backends and factory."""

from __future__ import annotations

import math

import pytest

from rag.embeddings import (
    DeterministicEmbedder,
    Embedder,
    get_embedder,
)
from rag.errors import EmbeddingError


def _norm(vector: tuple[float, ...]) -> float:
    return math.sqrt(sum(value * value for value in vector))


class TestDeterministicEmbedder:
    def test_default_dimension(self) -> None:
        assert DeterministicEmbedder().dimension == 128

    def test_custom_dimension(self) -> None:
        assert DeterministicEmbedder(dimension=64).dimension == 64

    def test_too_small_dimension_rejected(self) -> None:
        with pytest.raises(ValueError):
            DeterministicEmbedder(dimension=4)

    def test_is_deterministic(self) -> None:
        embedder = DeterministicEmbedder()
        first = embedder.embed_one("Photosynthesis happens in chloroplasts")
        second = embedder.embed_one("Photosynthesis happens in chloroplasts")
        assert first == second

    def test_same_shape_across_texts(self) -> None:
        embedder = DeterministicEmbedder()
        vectors = embedder.embed(["short", "a considerably longer sentence to hash"])
        assert all(len(vector) == 128 for vector in vectors)

    def test_distinct_texts_get_distinct_vectors(self) -> None:
        embedder = DeterministicEmbedder()
        assert (
            embedder.embed_one("operating systems scheduling queues")
            != embedder.embed_one("linear algebra vector spaces")
        )

    def test_vectors_are_unit_length(self) -> None:
        embedder = DeterministicEmbedder()
        text = "the Calvin cycle fixes carbon dioxide into glucose"
        norm = _norm(embedder.embed_one(text))
        assert norm == pytest.approx(1.0, abs=1e-9)

    def test_embed_matches_embed_one(self) -> None:
        embedder = DeterministicEmbedder()
        text = "round robin scheduling time slice"
        assert embedder.embed([text, text + "!"])[0] == embedder.embed_one(text)

    def test_cached_texts_share_the_same_vector_object(self) -> None:
        embedder = DeterministicEmbedder()
        text = "normalize the database into third normal form"
        assert embedder.embed_one(text) is embedder.embed_one(text)

    def test_repeated_embed_does_not_change(self) -> None:
        embedder = DeterministicEmbedder()
        before = embedder.embed(["a", "b", "a"])
        after = embedder.embed(["a", "b", "a"])
        assert before == after

    def test_blank_text_raises_embedding_error(self) -> None:
        embedder = DeterministicEmbedder()
        with pytest.raises(EmbeddingError):
            embedder.embed_one("   ")

    def test_empty_text_raises_embedding_error(self) -> None:
        embedder = DeterministicEmbedder()
        with pytest.raises(EmbeddingError):
            embedder.embed_one("")

    def test_none_text_raises_embedding_error(self) -> None:
        embedder = DeterministicEmbedder()
        with pytest.raises(EmbeddingError):
            embedder.embed([None])  # type: ignore[list-item]

    def test_batch_with_a_blank_entry_raises(self) -> None:
        embedder = DeterministicEmbedder()
        with pytest.raises(EmbeddingError):
            embedder.embed(["fine", "   \n"])


class TestEmbedderFactory:
    def test_deterministic_backend(self) -> None:
        assert isinstance(get_embedder("deterministic"), DeterministicEmbedder)

    def test_unknown_backend_rejected(self) -> None:
        with pytest.raises(ValueError):
            get_embedder("not-a-backend")

    def test_auto_backend_returns_an_embedder(self) -> None:
        # Deterministic when sentence-transformers is unavailable (as here),
        # sentence-transformers when it is importable.
        assert isinstance(get_embedder("auto"), Embedder)