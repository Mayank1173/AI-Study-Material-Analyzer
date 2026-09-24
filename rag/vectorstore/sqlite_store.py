"""SQLite-backed vector store with numpy cosine similarity search.

Schema::

    chunks(
        chunk_id      TEXT PRIMARY KEY,   -- "{material_id}:{chunk_index}"
        material_id   TEXT NOT NULL,
        course_id     TEXT NOT NULL,
        uploaded_by   TEXT NOT NULL,
        text          TEXT NOT NULL,
        metadata_json TEXT NOT NULL,      -- JSON serialization of ChunkMetadata
        embedding     BLOB NOT NULL       -- little-endian float32 vector
    )
    store_meta(
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )   -- stores "embedding_dimension"
    visuals(
        visual_id        TEXT PRIMARY KEY, -- "{material_id}:p{page}" etc.
        material_id      TEXT NOT NULL,
        course_id        TEXT NOT NULL,
        uploaded_by      TEXT NOT NULL,
        page             INTEGER,
        slide            INTEGER,
        source_location  TEXT NOT NULL,
        visual_type      TEXT NOT NULL,   -- diagram/figure/chart/table/...
        caption          TEXT NOT NULL,
        nearby_text      TEXT NOT NULL,
        description      TEXT NOT NULL,   -- always empty: pixels are never decoded
        original_filename TEXT,
        material_title   TEXT
    )

The first insert fixates the store's embedding dimension. Reopening a store
whose recorded dimension disagrees with incoming vectors raises
:class:`InvalidVectorError`; an unreadable file or inconsistent schema raises
:class:`VectorStoreUnavailableError`/:class:`VectorStoreCorruptedError`.
Error messages never include absolute filesystem paths. Visual elements have
no embeddings; they are searched with keyword overlap via
:meth:`search_visuals` and share the same ownership scoping as chunks.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

import numpy as np

from rag.errors import (
    DuplicateChunkError,
    InvalidVectorError,
    VectorStoreCorruptedError,
    VectorStoreUnavailableError,
)
from rag.models import (
    ChunkMetadata,
    IndexedChunk,
    SearchResult,
    VisualElement,
)
from rag.vectorstore.base import SearchFilter, VectorStore

_META_DIMENSION = "embedding_dimension"
_FLOAT32_SIZE = np.dtype(np.float32).itemsize

#: Keywords that never match anything meaningful in a visual query. Kept tiny
#: on purpose - visual search is keyword overlap, not embeddings.
_STOPWORDS = frozenset(
    {"the", "and", "for", "what", "which", "explain", "this", "that", "about"}
)


def _metadata_to_json(metadata: ChunkMetadata) -> str:
    return json.dumps(metadata.__dict__)


def _metadata_from_json(raw: str) -> ChunkMetadata:
    try:
        return ChunkMetadata(**json.loads(raw))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise VectorStoreCorruptedError(
            "metadata in the vector store could not be decoded"
        ) from exc


def _visual_row(visual: VisualElement, uploaded_by: str) -> tuple:
    return (
        visual.visual_id,
        visual.material_id or "",
        visual.course_id or "",
        uploaded_by,
        visual.page,
        visual.slide,
        visual.source_location or "",
        visual.visual_type,
        visual.caption or "",
        visual.nearby_text or "",
        visual.description or "",
        visual.original_filename,
        visual.material_title,
    )


def _visual_from_row(row: sqlite3.Row) -> VisualElement:
    return VisualElement(
        visual_id=row["visual_id"],
        material_id=row["material_id"],
        course_id=row["course_id"] or None,
        original_filename=row["original_filename"],
        material_title=row["material_title"],
        page=row["page"],
        slide=row["slide"],
        source_location=row["source_location"] or None,
        visual_type=row["visual_type"],
        caption=row["caption"],
        nearby_text=row["nearby_text"],
        description=row["description"],
    )


def _visual_terms(query: str) -> list[str]:
    raw = "".join(ch if ch.isalnum() else " " for ch in (query or "").lower())
    return [tok for tok in raw.split() if len(tok) >= 3 and tok not in _STOPWORDS]


def _visual_score(visual: VisualElement, terms: list[str]) -> int:
    caption = (visual.caption or "").lower()
    visual_type = (visual.visual_type or "").lower()
    nearby = (visual.nearby_text or "").lower()
    description = (visual.description or "").lower()
    title = (visual.material_title or "").lower()
    filename = (visual.original_filename or "").lower()
    location = (visual.source_location or "").lower()

    score = 0
    for term in terms:
        if term in caption or term in visual_type:
            score += 3
        elif term in nearby or term in description:
            score += 2
        elif term in title or term in filename or term in location:
            score += 1
    return score


def _embedding_to_bytes(vector: tuple[float, ...]) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def _embedding_from_bytes(raw: bytes, dimension: int) -> np.ndarray:
    if len(raw) != dimension * _FLOAT32_SIZE:
        raise VectorStoreCorruptedError(
            "an embedding in the vector store has the wrong byte length"
        )
    vector = np.frombuffer(raw, dtype=np.float32)
    if not np.all(np.isfinite(vector)):
        raise VectorStoreCorruptedError(
            "an embedding in the vector store contains non-finite values"
        )
    return vector.astype(np.float64)


class SqliteVectorStore(VectorStore):
    """Persistent vector store backed by a single SQLite file."""

    def __init__(self, store_path: str | Path) -> None:
        self._path = Path(store_path)
        self._closed = False
        self._dimension: int | None = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(
                str(self._path), timeout=30, check_same_thread=False
            )
            self._conn.row_factory = sqlite3.Row
        except (OSError, sqlite3.Error) as exc:
            raise VectorStoreUnavailableError(
                "the vector store could not be opened"
            ) from exc
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        try:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id      TEXT PRIMARY KEY,
                    material_id   TEXT NOT NULL,
                    course_id     TEXT NOT NULL,
                    uploaded_by   TEXT NOT NULL,
                    text          TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    embedding     BLOB NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS visuals (
                    visual_id        TEXT PRIMARY KEY,
                    material_id      TEXT NOT NULL,
                    course_id        TEXT NOT NULL,
                    uploaded_by      TEXT NOT NULL,
                    page             INTEGER,
                    slide            INTEGER,
                    source_location  TEXT NOT NULL,
                    visual_type      TEXT NOT NULL,
                    caption          TEXT NOT NULL,
                    nearby_text      TEXT NOT NULL,
                    description      TEXT NOT NULL,
                    original_filename TEXT,
                    material_title   TEXT
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS store_meta (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_material ON chunks(material_id)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_course ON chunks(course_id)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_owner ON chunks(uploaded_by)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_visuals_material ON visuals(material_id)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_visuals_course ON visuals(course_id)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_visuals_owner ON visuals(uploaded_by)"
            )
            self._conn.commit()
        except sqlite3.Error as exc:  # pragma: no cover - schema is static
            raise VectorStoreCorruptedError(
                "the vector store schema is missing or incompatible"
            ) from exc

        row = self._conn.execute(
            "SELECT value FROM store_meta WHERE key = ?", (_META_DIMENSION,)
        ).fetchone()
        if row is not None:
            try:
                self._dimension = int(row["value"])
            except (TypeError, ValueError) as exc:
                raise VectorStoreCorruptedError(
                    "the vector store dimension record is invalid"
                ) from exc

    @property
    def dimension(self) -> int | None:
        return self._dimension

    def _ensure_open(self) -> None:
        if self._closed:
            raise VectorStoreUnavailableError(
                "the vector store is closed and cannot be used"
            )

    @staticmethod
    def _validate_vector(
        vector: tuple[float, ...],
        expected_dimension: int | None,
    ) -> np.ndarray:
        try:
            array = np.asarray(vector, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise InvalidVectorError(
                "an embedding vector is not a flat numeric array"
            ) from exc
        if array.ndim != 1:
            raise InvalidVectorError("an embedding vector must be one-dimensional")
        if expected_dimension is not None and array.shape[0] != expected_dimension:
            raise InvalidVectorError(
                f"an embedding vector has the wrong dimension "
                f"(expected {expected_dimension})"
            )
        if not np.all(np.isfinite(array)):
            raise InvalidVectorError(
                "an embedding vector contains non-finite values"
            )
        norm = float(np.linalg.norm(array))
        if norm <= 0.0:
            raise InvalidVectorError("an embedding vector has zero magnitude")
        return array

    def add(self, chunks: Iterable[IndexedChunk]) -> int:
        self._ensure_open()
        materialized = list(chunks)
        if not materialized:
            return 0

        vectors = [
            self._validate_vector(chunk.embedding, self._dimension)
            for chunk in materialized
        ]
        first_dim = int(vectors[0].shape[0])
        if self._dimension is None:
            self._dimension = first_dim

        rows = []
        for chunk, vector in zip(materialized, vectors):
            rows.append(
                (
                    chunk.chunk_id,
                    chunk.material_id,
                    chunk.course_id,
                    chunk.uploaded_by,
                    chunk.text,
                    _metadata_to_json(chunk.metadata),
                    _embedding_to_bytes(vector),
                )
            )
        try:
            with self._conn:
                self._conn.executemany(
                    """
                    INSERT INTO chunks (
                        chunk_id, material_id, course_id, uploaded_by,
                        text, metadata_json, embedding
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                self._conn.execute(
                    "INSERT OR REPLACE INTO store_meta (key, value) VALUES (?, ?)",
                    (_META_DIMENSION, str(self._dimension)),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateChunkError(
                "a chunk with this identifier is already indexed"
            ) from exc
        except sqlite3.Error as exc:
            raise VectorStoreUnavailableError(
                "the vector store could not be written to"
            ) from exc
        return len(rows)

    def delete_material(self, material_id: str) -> int:
        self._ensure_open()
        cursor = self._conn.execute(
            "DELETE FROM chunks WHERE material_id = ?", (material_id,)
        )
        self._conn.execute(
            "DELETE FROM visuals WHERE material_id = ?", (material_id,)
        )
        self._conn.commit()
        return int(cursor.rowcount)

    def add_visuals(
        self, visuals: Iterable[VisualElement], *, uploaded_by: str
    ) -> int:
        """Persist visual elements for the given owner; returns rows written."""
        self._ensure_open()
        materialized = list(visuals)
        if not materialized:
            return 0
        rows = [_visual_row(visual, uploaded_by) for visual in materialized]
        try:
            with self._conn:
                self._conn.executemany(
                    """
                    INSERT OR REPLACE INTO visuals (
                        visual_id, material_id, course_id, uploaded_by,
                        page, slide, source_location, visual_type,
                        caption, nearby_text, description,
                        original_filename, material_title
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
        except sqlite3.Error as exc:
            raise VectorStoreUnavailableError(
                "the vector store could not be written to"
            ) from exc
        return len(rows)

    def search_visuals(
        self,
        query: str,
        filter: SearchFilter,
        top_k: int = 5,
    ) -> list[VisualElement]:
        """Keyword search over visual metadata, scoped by ownership.

        Visual elements do not have embeddings; scoring is a lightweight
        term-overlap against caption, type, nearby text, and source record.
        """
        self._ensure_open()
        if top_k < 1:
            return []
        terms = _visual_terms(query)
        if not terms:
            return []

        clauses = ["uploaded_by = ?"]
        params: list[object] = [filter.user_id]
        if filter.course_id:
            clauses.append("course_id = ?")
            params.append(filter.course_id)
        if filter.material_id:
            clauses.append("material_id = ?")
            params.append(filter.material_id)
        where = " AND ".join(clauses)

        try:
            rows = self._conn.execute(
                f"""
                SELECT visual_id, material_id, course_id, page, slide,
                       source_location, visual_type, caption, nearby_text,
                       description, original_filename, material_title
                FROM visuals WHERE {where}
                """,
                params,
            ).fetchall()
        except sqlite3.Error as exc:
            raise VectorStoreUnavailableError(
                "the vector store could not be queried"
            ) from exc

        scored: list[tuple[int, str, VisualElement]] = []
        for row in rows:
            visual = _visual_from_row(row)
            score = _visual_score(visual, terms)
            if score > 0:
                scored.append((score, visual.visual_id, visual))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [visual for _, _, visual in scored[:top_k]]

    def count_visuals(self, filter: SearchFilter | None = None) -> int:
        self._ensure_open()
        where = ""
        params: list[object] = []
        if filter is not None:
            clauses = ["uploaded_by = ?"]
            params.append(filter.user_id)
            if filter.course_id:
                clauses.append("course_id = ?")
                params.append(filter.course_id)
            if filter.material_id:
                clauses.append("material_id = ?")
                params.append(filter.material_id)
            where = " WHERE " + " AND ".join(clauses)
        row = self._conn.execute(
            f"SELECT COUNT(*) AS n FROM visuals{where}", params
        ).fetchone()
        return int(row["n"])

    def search(
        self,
        query_vector: tuple[float, ...],
        filter: SearchFilter,
        top_k: int = 5,
    ) -> list[SearchResult]:
        self._ensure_open()
        if top_k < 1:
            return []
        if self._dimension is None:
            self._validate_vector(query_vector, None)
            return []

        query = self._validate_vector(query_vector, self._dimension)
        query = query / float(np.linalg.norm(query))

        clauses = ["uploaded_by = ?"]
        params: list[object] = [filter.user_id]
        if filter.course_id:
            clauses.append("course_id = ?")
            params.append(filter.course_id)
        if filter.material_id:
            clauses.append("material_id = ?")
            params.append(filter.material_id)
        where = " AND ".join(clauses)

        try:
            rows = self._conn.execute(
                f"""
                SELECT chunk_id, material_id, course_id, uploaded_by,
                       text, metadata_json, embedding
                FROM chunks WHERE {where}
                """,
                params,
            ).fetchall()
        except sqlite3.Error as exc:
            raise VectorStoreUnavailableError(
                "the vector store could not be queried"
            ) from exc

        scored: list[tuple[float, str, SearchResult]] = []
        for row in rows:
            embedding = _embedding_from_bytes(
                bytes(row["embedding"]), self._dimension
            )
            norm = float(np.linalg.norm(embedding))
            if norm <= 0.0:
                raise VectorStoreCorruptedError(
                    "an embedding in the vector store has zero magnitude"
                )
            embedding = embedding / norm
            score = float(np.dot(embedding, query))
            scored.append(
                (
                    score,
                    row["chunk_id"],
                    SearchResult(
                        chunk_id=row["chunk_id"],
                        material_id=row["material_id"],
                        course_id=row["course_id"],
                        uploaded_by=row["uploaded_by"],
                        text=row["text"],
                        score=score,
                        metadata=_metadata_from_json(row["metadata_json"]),
                    ),
                )
            )

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [result for _, _, result in scored[:top_k]]

    def count(self, filter: SearchFilter | None = None) -> int:
        self._ensure_open()
        where = ""
        params: list[object] = []
        if filter is not None:
            clauses = ["uploaded_by = ?"]
            params.append(filter.user_id)
            if filter.course_id:
                clauses.append("course_id = ?")
                params.append(filter.course_id)
            if filter.material_id:
                clauses.append("material_id = ?")
                params.append(filter.material_id)
            where = " WHERE " + " AND ".join(clauses)
        row = self._conn.execute(f"SELECT COUNT(*) AS n FROM chunks{where}", params).fetchone()
        return int(row["n"])

    def close(self) -> None:
        if self._closed:
            return
        self._conn.close()
        self._closed = True