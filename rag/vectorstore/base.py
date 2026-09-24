"""Abstract vector store interface and shared filter types.

A vector store persists chunk embeddings plus their source metadata and
answers semantic-similarity queries. The concrete SQLite implementation lives
in :mod:`rag.vectorstore.sqlite_store`; swapping in another backend only
requires implementing this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass

from rag.models import IndexedChunk, SearchResult


@dataclass(frozen=True)
class SearchFilter:
    """Ownership/scope constraints for a vector-store search.

    ``user_id`` is always required: a search can never be issued without
    knowing which user's chunks are eligible. This is the multi-tenant
    security boundary - ``course_id`` alone is never enough to scope a query.
    ``course_id`` and ``material_id`` optionally narrow the eligible set.
    """

    user_id: str
    course_id: str | None = None
    material_id: str | None = None

    def __post_init__(self) -> None:
        if not self.user_id or not str(self.user_id).strip():
            raise ValueError("SearchFilter.user_id must be a non-empty string")


class VectorStore(ABC):
    """Persistent store of normalized embeddings plus source metadata.

    Implementations must keep every chunk scoped to its owner (``uploaded_by``)
    and never return another user's chunks when filtered by an arbitrary user.
    """

    @property
    @abstractmethod
    def dimension(self) -> int | None:
        """Fixed embedding dimensionality, or ``None`` while the store is empty."""

    @abstractmethod
    def add(self, chunks: Iterable[IndexedChunk]) -> int:
        """Index chunks; returns how many were added.

        The first insert fixates the store's embedding dimension. Duplicate
        ``chunk_id`` raises :class:`DuplicateChunkError`.
        """

    @abstractmethod
    def delete_material(self, material_id: str) -> int:
        """Delete every chunk belonging to ``material_id``; returns count removed.

        Deleting a material that has no chunks is a no-op returning 0.
        """

    @abstractmethod
    def search(
        self,
        query_vector: tuple[float, ...],
        filter: SearchFilter,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Return up to ``top_k`` chunks ranked by cosine similarity to the query.

        The query vector must match this store's dimensionality and be finite.
        """

    @abstractmethod
    def count(self, filter: SearchFilter | None = None) -> int:
        """Count indexed chunks, optionally scoped by a filter."""

    @abstractmethod
    def close(self) -> None:
        """Release resources; safe to call multiple times."""