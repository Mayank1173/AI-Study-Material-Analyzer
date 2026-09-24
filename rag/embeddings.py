"""Pluggable text embeddings for the knowledge base.

Two backends ship with the package:

1. :class:`DeterministicEmbedder` - a dependency-free, repeatable embedding
   built from word and character n-gram hashes. It is the default, used by
   tests and offline setups where no model weights are available.
2. :class:`SentenceTransformersEmbedder` - an optional real model backend
   (default ``all-MiniLM-L6-v2``) with no API key; it is only importable when
   ``sentence-transformers`` is installed.

Both produce L2-normalized unit vectors so cosine similarity is a plain dot
product. Embeddings are cached by text, so re-indexing identical chunks is
cheap.
"""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from collections.abc import Iterable

from rag.errors import (
    EmbeddingError,
    EmbeddingModelUnavailableError,
)


class Embedder(ABC):
    """Abstract contract for any text-to-vector backend."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Fixed dimensionality of every produced vector."""

    @abstractmethod
    def embed(self, texts: Iterable[str]) -> list[tuple[float, ...]]:
        """Embed many texts at once, returning one vector per text.

        Vectors are tuples of floats and must be L2-normalized (length 1).
        """

    def embed_one(self, text: str) -> tuple[float, ...]:
        """Embed a single text. Invalid/empty input raises :class:`EmbeddingError`."""
        vectors = self.embed((text,))
        return vectors[0]


class DeterministicEmbedder(Embedder):
    """Repeatable, dependency-free fixed-size embedding via cached n-gram hashing.

    Not semantically powerful, but deterministic across processes/machines and
    fast enough for tests. ``all_MiniLM_L6_v2`` provides real semantics when
    installed; this class is the faithful offline fallback.

    Each token is placed into a small, fixed number of hash buckets so short
    queries do not saturate the whole vector: with one uint32 bucket per digest
    chunk the trigrams of a short query already touched nearly every dimension,
    which made every pair of documents look similar.
    """

    _MAX_BUCKETS_PER_TOKEN = 2

    def __init__(self, dimension: int = 128) -> None:
        if dimension < 8:
            raise ValueError("dimension must be at least 8")
        self._dimension = dimension
        self._cache: dict[str, tuple[float, ...]] = {}

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Iterable[str]) -> list[tuple[float, ...]]:
        vectors: list[tuple[float, ...]] = []
        for text in texts:
            if text is None or not str(text).strip():
                raise EmbeddingError("cannot embed empty or blank text")
            normalized = " ".join(str(text).lower().split())
            cached = self._cache.get(normalized)
            if cached is None:
                cached = self._vectorize(normalized)
                self._cache[normalized] = cached
            vectors.append(cached)
        return vectors

    def _vectorize(self, text: str) -> tuple[float, ...]:
        vector = [0.0] * self._dimension
        tokens = text.split()
        # one-way hash bucket placement for each word and each char-trigram
        for word in tokens:
            for bucket in self._buckets_for(word):
                vector[bucket] += 1.0
        for i in range(len(text) - 2):
            for bucket in self._buckets_for(text[i : i + 3]):
                vector[bucket] += 1.0
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0.0:
            return tuple([0.0] * self._dimension)
        scale = 1.0 / magnitude
        return tuple(value * scale for value in vector)

    def _buckets_for(self, token: str) -> set[int]:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        buckets: set[int] = set()
        for offset in range(0, len(digest) - 3, 4):
            value = int.from_bytes(digest[offset : offset + 4], "little")
            buckets.add(value % self._dimension)
            if len(buckets) >= self._MAX_BUCKETS_PER_TOKEN:
                break
        return buckets


class SentenceTransformersEmbedder(Embedder):
    """Optional real-model embedding backend using ``sentence-transformers``.

    Uses a local, open-source model (default ``all-MiniLM-L6-v2``, 384 dims).
    The model is cached locally by sentence-transformers; no API key or network
    service is required after the initial download. Instantiation raises
    :class:`EmbeddingModelUnavailableError` when the package is not installed.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise EmbeddingModelUnavailableError(
                "the sentence-transformers package is not installed"
            ) from exc
        try:
            self._model = SentenceTransformer(model_name)
        except Exception as exc:  # pragma: no cover - network/model dependent
            raise EmbeddingModelUnavailableError(
                f"could not load embedding model {model_name!r}"
            ) from exc
        self._dimension = int(self._model.get_sentence_embedding_dimension())
        self._cache: dict[str, tuple[float, ...]] = {}

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Iterable[str]) -> list[tuple[float, ...]]:
        unique = [text for text in texts if text and str(text).strip()]
        missing = [text for text in unique if text not in self._cache]
        if missing:
            import numpy as np

            encoded = self._model.encode(
                missing,
                normalize_embeddings=True,
                convert_to_numpy=True,
                batch_size=32,
            )
            for text, vector in zip(missing, encoded.tolist()):
                self._cache[text] = tuple(float(value) for value in vector)
        return [self._cache[text] for text in texts]

    def close(self) -> None:
        self._cache.clear()
        self._model = None


def get_embedder(
    backend: str = "auto",
    model_name: str = "all-MiniLM-L6-v2",
) -> Embedder:
    """Create an embedder for the requested backend.

    ``backend`` must be one of ``"auto"``, ``"deterministic"``, or
    ``"sentence-transformers"``. ``"auto"`` uses sentence-transformers when
    available and falls back to the deterministic embedder otherwise.
    """
    normalized = backend.lower().strip()
    if normalized == "deterministic":
        return DeterministicEmbedder()
    if normalized == "sentence-transformers":
        return SentenceTransformersEmbedder(model_name=model_name)
    if normalized == "auto":
        try:
            import sentence_transformers  # noqa: F401  (importability check)

            return SentenceTransformersEmbedder(model_name=model_name)
        except Exception:
            return DeterministicEmbedder()
    raise ValueError(
        f"unknown embedding backend {backend!r}; "
        "expected 'auto', 'deterministic', or 'sentence-transformers'"
    )