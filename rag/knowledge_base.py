"""Phase 2 knowledge base: embedding + indexing + semantic search.

The :class:`KnowledgeBase` composes the Phase 1 pipeline
(:func:`rag.pipeline.process_document`) with an :class:`Embedder` and a
:class:`VectorStore` (default: SQLite + numpy cosine). Every chunk is stored
with its owner (``uploaded_by``) and every search is always scoped by the
requester's user id - course/material filters can only narrow that set, never
broaden it.
"""

from __future__ import annotations

from pathlib import Path

from rag.config import get_rag_settings
from rag.embeddings import Embedder, get_embedder
from rag.errors import (
    EmptyQueryError,
    IndexingError,
)
from rag.models import IndexedChunk, ProcessedDocument, SearchResult, SourceRef
from rag.pipeline import process_document
from rag.vectorstore.base import SearchFilter, VectorStore
from rag.vectorstore.sqlite_store import SqliteVectorStore

DEFAULT_CHUNK_SIZE = 1500
DEFAULT_CHUNK_OVERLAP = 150


def _course_id_for(document: ProcessedDocument) -> str:
    return document.source.course_id or ""


class KnowledgeBase:
    """Searchable index of processed study materials for a group of users.

    The knowledge base is material-centric: indexing any material removes and
    replaces that material's existing chunks, so re-indexing never duplicates.
    """

    def __init__(self, embedder: Embedder, store: VectorStore) -> None:
        self._embedder = embedder
        self._store = store

    @property
    def dimension(self) -> int | None:
        return self._store.dimension

    def index_material(
        self,
        source: str | Path,
        *,
        source_ref: SourceRef,
        uploaded_by: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
        file_type: str | None = None,
    ) -> int:
        """Process a stored document and index all of its chunks.

        Returns the number of chunks indexed (0 when the document, while valid,
        produced no chunks). Re-indexing the same material replaces its prior
        chunks.
        """
        document = process_document(
            source,
            source_ref=source_ref,
            file_type=file_type,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        return self.index_processed(document, uploaded_by=uploaded_by)

    def index_processed(
        self, document: ProcessedDocument, *, uploaded_by: str
    ) -> int:
        """Embed an already-processed document's chunks and index them.

        ``uploaded_by`` is the owning user's id and is required. The material is
        wiped from the index first so re-indexing is always idempotent.
        """
        material_id = document.source.material_id
        if not material_id:
            raise IndexingError("a material id is required to index a document")
        if not uploaded_by or not uploaded_by.strip():
            raise IndexingError("the uploading user id is required to index")

        course_id = _course_id_for(document)
        self._store.delete_material(material_id)

        chunks = document.chunks
        if not chunks:
            return 0

        try:
            embeddings = self._embedder.embed([chunk.text for chunk in chunks])
            indexed = [
                IndexedChunk.from_text_chunk(
                    chunk,
                    chunk_id=f"{material_id}:{index}",
                    material_id=material_id,
                    course_id=course_id,
                    uploaded_by=uploaded_by,
                    embedding=embeddings[index],
                )
                for index, chunk in enumerate(chunks)
            ]
        except Exception as exc:
            raise IndexingError(
                "the document could not be embedded and indexed"
            ) from exc

        return self._store.add(indexed)

    def delete_material(self, material_id: str) -> int:
        """Remove every chunk belonging to a material; returns count removed."""
        return self._store.delete_material(material_id)

    def search(
        self,
        query: str,
        *,
        user_id: str,
        course_id: str | None = None,
        material_id: str | None = None,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Semantic search scoped to ``user_id`` with optional narrowing.

        ``user_id`` is mandatory and enforced by :class:`SearchFilter`; without
        it a search is refused rather than returning another user's chunks.
        """
        if not query or not query.strip():
            raise EmptyQueryError("a non-empty search query is required")
        query_vector = self._embedder.embed_one(query.strip())
        return self._store.search(
            query_vector,
            SearchFilter(
                user_id=user_id,
                course_id=course_id,
                material_id=material_id,
            ),
            top_k=top_k,
        )

    def embed(self, texts: list[str]) -> list[tuple[float, ...]]:
        """Embed arbitrary texts with this knowledge base's embedder.

        Exposes the configured embedding backend so other features (for example
        PYQ question clustering) can reuse the same vectors as retrieval instead
        of reaching into private state or building a second embedder.
        """
        return self._embedder.embed(texts)

    def count(
        self,
        user_id: str | None = None,
        course_id: str | None = None,
        material_id: str | None = None,
    ) -> int:
        """Number of indexed chunks, optionally scoped to a user/material."""
        if user_id is None and course_id is None and material_id is None:
            return self._store.count()
        return self._store.count(
            SearchFilter(
                user_id=user_id or "",
                course_id=course_id,
                material_id=material_id,
            )
        )

    def close(self) -> None:
        close_embedder = getattr(self._embedder, "close", None)
        if callable(close_embedder):
            close_embedder()
        self._store.close()


def get_knowledge_base(
    *,
    store_path: str | Path | None = None,
    embedding_backend: str | None = None,
    embedding_model: str | None = None,
) -> KnowledgeBase:
    """Build a :class:`KnowledgeBase` from settings (args, then env, then defaults)."""
    settings = get_rag_settings(
        vector_store_path=store_path,
        embedding_backend=embedding_backend,
        embedding_model=embedding_model,
    )
    embedder = get_embedder(settings.embedding_backend, settings.embedding_model)
    store = SqliteVectorStore(settings.vector_store_path)
    return KnowledgeBase(embedder, store)