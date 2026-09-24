"""Tests for the SQLite-backed vector store."""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path

import pytest

from rag.errors import (
    DuplicateChunkError,
    InvalidVectorError,
    VectorStoreCorruptedError,
    VectorStoreUnavailableError,
)
from rag.models import ChunkMetadata, IndexedChunk
from rag.vectorstore import SearchFilter, SqliteVectorStore

AXIS = {
    0: (1.0, 0.0, 0.0, 0.0),
    1: (0.0, 1.0, 0.0, 0.0),
    2: (0.0, 0.0, 1.0, 0.0),
    3: (0.0, 0.0, 0.0, 1.0),
}


def _make_chunk(
    text: str,
    *,
    material_id: str = "mat-1",
    course_id: str = "course-1",
    uploaded_by: str = "user-1",
    chunk_index: int = 0,
    embedding: tuple[float, ...] = AXIS[0],
) -> IndexedChunk:
    metadata = ChunkMetadata(
        material_id=material_id,
        course_id=course_id,
        original_filename="lecture.txt",
        material_title="Lecture",
        source_type=".txt",
        chunk_index=chunk_index,
        total_chunks=1,
    )
    return IndexedChunk(
        chunk_id=f"{material_id}:{chunk_index}",
        material_id=material_id,
        course_id=course_id,
        uploaded_by=uploaded_by,
        text=text,
        embedding=embedding,
        metadata=metadata,
    )


@pytest.fixture()
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "kb.db"


@pytest.fixture()
def store(store_path: Path) -> SqliteVectorStore:
    instance = SqliteVectorStore(store_path)
    yield instance
    instance.close()


class TestAddAndCount:
    def test_add_returns_row_count(self, store: SqliteVectorStore) -> None:
        assert (
            store.add(
                [
                    _make_chunk("first", chunk_index=0),
                    _make_chunk("second", chunk_index=1),
                ]
            )
            == 2
        )

    def test_count_after_add(self, store: SqliteVectorStore) -> None:
        store.add(
            [
                _make_chunk("first", chunk_index=0),
                _make_chunk("second", chunk_index=1),
            ]
        )
        assert store.count() == 2

    def test_count_scoped_by_user(self, store: SqliteVectorStore) -> None:
        store.add(
            [
                _make_chunk("mine", uploaded_by="alice", chunk_index=0),
                _make_chunk("mine2", uploaded_by="alice", chunk_index=1),
                _make_chunk("yours", uploaded_by="bob", material_id="mat-2", chunk_index=0),
            ]
        )
        assert store.count(SearchFilter(user_id="alice")) == 2
        assert store.count(SearchFilter(user_id="bob")) == 1

    def test_count_scoped_by_course_and_material(self, store: SqliteVectorStore) -> None:
        store.add(
            [
                _make_chunk("a", course_id="c1", material_id="m1", chunk_index=0),
                _make_chunk("b", course_id="c1", material_id="m1", chunk_index=1),
                _make_chunk("c", course_id="c2", material_id="m2", chunk_index=0),
            ]
        )
        assert store.count(SearchFilter(user_id="user-1", course_id="c1")) == 2
        assert (
            store.count(
                SearchFilter(user_id="user-1", course_id="c1", material_id="m1")
            )
            == 2
        )

    def test_empty_add_is_noop(self, store: SqliteVectorStore) -> None:
        assert store.add([]) == 0
        assert store.count() == 0

    def test_empty_store_has_no_dimension(self, store: SqliteVectorStore) -> None:
        assert store.dimension is None

    def test_dimension_is_fixed_by_first_add(self, store: SqliteVectorStore) -> None:
        store.add([_make_chunk("first")])
        assert store.dimension == 4

    def test_duplicate_chunk_id_raises(self, store: SqliteVectorStore) -> None:
        store.add([_make_chunk("first", chunk_index=0)])
        with pytest.raises(DuplicateChunkError):
            store.add([_make_chunk("duplicate", chunk_index=0)])

    def test_interleaved_insert_with_duplicate_keeps_transaction(
        self, store: SqliteVectorStore
    ) -> None:
        store.add([_make_chunk("existing", chunk_index=0)])
        with pytest.raises(DuplicateChunkError):
            store.add(
                [
                    _make_chunk("fresh", chunk_index=1),
                    _make_chunk("again", chunk_index=0),
                ]
            )
        # The whole batch rolled back: only the original chunk remains.
        assert store.count() == 1


class TestAddValidation:
    def test_wrong_dimension_raises(self, store: SqliteVectorStore) -> None:
        store.add([_make_chunk("seed", chunk_index=0)])
        with pytest.raises(InvalidVectorError):
            store.add([_make_chunk("bad", chunk_index=1, embedding=(0.0, 0.0, 0.0))])

    def test_two_dimensional_vector_rejected_on_empty_store(
        self, store: SqliteVectorStore
    ) -> None:
        with pytest.raises(InvalidVectorError):
            store.add([_make_chunk("bad", chunk_index=0, embedding=((1.0, 0.0),))])

    def test_non_finite_values_rejected(self, store: SqliteVectorStore) -> None:
        with pytest.raises(InvalidVectorError):
            store.add(
                [
                    _make_chunk(
                        "nan", chunk_index=0, embedding=(float("nan"), 0.0, 0.0, 0.0)
                    )
                ]
            )

    def test_zero_magnitude_vector_rejected(self, store: SqliteVectorStore) -> None:
        with pytest.raises(InvalidVectorError):
            store.add([_make_chunk("zero", chunk_index=0, embedding=(0.0, 0.0, 0.0, 0.0))])

    def test_dimension_must_match_persisted_store(self, store_path: Path) -> None:
        first = SqliteVectorStore(store_path)
        first.add([_make_chunk("seed", chunk_index=0)])
        first.close()

        second = SqliteVectorStore(store_path)
        try:
            with pytest.raises(InvalidVectorError):
                second.add(
                    [_make_chunk("bad", chunk_index=1, embedding=(0.0, 0.0, 0.0))]
                )
        finally:
            second.close()


class TestSearch:
    def test_top_hit_matches_query_vector(self, store: SqliteVectorStore) -> None:
        store.add(
            [
                _make_chunk("perp-1", chunk_index=0, embedding=AXIS[1]),
                _make_chunk("query-mate", chunk_index=1, embedding=AXIS[0]),
            ]
        )
        results = store.search(AXIS[0], SearchFilter(user_id="user-1"))
        assert results[0].chunk_id == "mat-1:1"
        assert results[0].score == pytest.approx(1.0)

    def test_rank_order(self, store: SqliteVectorStore) -> None:
        store.add(
            [
                _make_chunk("a", chunk_index=0, embedding=AXIS[0]),
                _make_chunk("b", chunk_index=1, embedding=AXIS[1]),
                _make_chunk("c", chunk_index=2, embedding=AXIS[2]),
            ]
        )
        chunk_ids = [r.chunk_id for r in store.search(AXIS[1], SearchFilter(user_id="user-1"))]
        assert chunk_ids == ["mat-1:1", "mat-1:0", "mat-1:2"]

    def test_top_k_limits_results(self, store: SqliteVectorStore) -> None:
        store.add(
            [
                _make_chunk(str(i), chunk_index=i, embedding=AXIS[i % 4])
                for i in range(4)
            ]
        )
        assert len(store.search(AXIS[0], SearchFilter(user_id="user-1"), top_k=2)) == 2

    def test_search_on_empty_store_returns_empty(self, store: SqliteVectorStore) -> None:
        assert (
            store.search(AXIS[0], SearchFilter(user_id="user-1"))
            == []
        )

    def test_ties_break_by_chunk_id(self, store: SqliteVectorStore) -> None:
        store.add(
            [
                _make_chunk("z-text", chunk_index=0, embedding=AXIS[1]),
                _make_chunk("a-text", chunk_index=1, embedding=AXIS[2]),
                _make_chunk("m-text", chunk_index=2, embedding=AXIS[3]),
            ]
        )
        chunk_ids = [r.chunk_id for r in store.search(AXIS[0], SearchFilter(user_id="user-1"))]
        assert chunk_ids == ["mat-1:0", "mat-1:1", "mat-1:2"]

    def test_string_payload_preserved(self, store: SqliteVectorStore) -> None:
        text = "Round-robin scheduling gives each process a fixed time slice."
        store.add([_make_chunk(text, chunk_index=0)])
        result = store.search(AXIS[0], SearchFilter(user_id="user-1"))
        assert result[0].text == text
        assert result[0].metadata.chunk_index == 0
        assert result[0].metadata.material_title == "Lecture"

    def test_query_vector_wrong_dimension_rejected(
        self, store: SqliteVectorStore
    ) -> None:
        store.add([_make_chunk("seed", chunk_index=0)])
        with pytest.raises(InvalidVectorError):
            store.search((0.0, 0.0, 0.0), SearchFilter(user_id="user-1"))

    def test_query_vector_non_finite_rejected(self, store: SqliteVectorStore) -> None:
        store.add([_make_chunk("seed", chunk_index=0)])
        with pytest.raises(InvalidVectorError):
            store.search(
                (float("inf"), 0.0, 0.0, 0.0), SearchFilter(user_id="user-1")
            )

    def test_query_vector_zero_rejected(self, store: SqliteVectorStore) -> None:
        store.add([_make_chunk("seed", chunk_index=0)])
        with pytest.raises(InvalidVectorError):
            store.search((0.0, 0.0, 0.0, 0.0), SearchFilter(user_id="user-1"))


class TestMultiTenancy:
    def test_owners_never_see_each_others_chunks(
        self, store: SqliteVectorStore
    ) -> None:
        store.add(
            [
                _make_chunk("alice secret", uploaded_by="alice", chunk_index=0),
                _make_chunk("bob secret", uploaded_by="bob", material_id="mat-2", chunk_index=0),
            ]
        )
        alice_only = [r.chunk_id for r in store.search(AXIS[0], SearchFilter(user_id="alice"))]
        bob_only = [r.chunk_id for r in store.search(AXIS[0], SearchFilter(user_id="bob"))]
        assert alice_only == ["mat-1:0"]
        assert bob_only == ["mat-2:0"]
        assert alice_only != bob_only

    def test_material_filter_does_not_breach_ownership(
        self, store: SqliteVectorStore
    ) -> None:
        # Identical text and course, different owners/materials: still isolated.
        store.add(
            [
                _make_chunk("shared note", uploaded_by="alice", chunk_index=0),
                _make_chunk("shared note", uploaded_by="bob", material_id="mat-2", chunk_index=0),
            ]
        )
        names = [
            r.text
            for r in store.search(
                AXIS[0], SearchFilter(user_id="bob", material_id="mat-2")
            )
        ]
        assert names == ["shared note"]
        assert store.search(
            AXIS[0], SearchFilter(user_id="bob", material_id="mat-1")
        ) == []

    def test_course_filter_with_other_owner_excludes(
        self, store: SqliteVectorStore
    ) -> None:
        store.add(
            [
                _make_chunk("alice in c1", uploaded_by="alice", course_id="c1", chunk_index=0),
                _make_chunk("bob in c1", uploaded_by="bob", material_id="mat-2", course_id="c1", chunk_index=0),
                _make_chunk("bob in c2", uploaded_by="bob", material_id="mat-2", course_id="c2", chunk_index=1),
            ]
        )
        results = store.search(
            AXIS[0], SearchFilter(user_id="bob", course_id="c1")
        )
        assert [r.text for r in results] == ["bob in c1"]

    def test_filter_without_owner_rejected(self) -> None:
        with pytest.raises(ValueError):
            SearchFilter(user_id="   ")


class TestDeletion:
    def test_delete_material_removes_only_that_material(
        self, store: SqliteVectorStore
    ) -> None:
        store.add(
            [
                _make_chunk("keep", material_id="m-keep", chunk_index=0),
                _make_chunk("gone", material_id="m-gone", chunk_index=0),
                _make_chunk("gone2", material_id="m-gone", chunk_index=1),
            ]
        )
        assert store.delete_material("m-gone") == 2
        assert store.count() == 1
        texts = [r.text for r in store.search(AXIS[0], SearchFilter(user_id="user-1"))]
        assert texts == ["keep"]

    def test_delete_missing_material_returns_zero(
        self, store: SqliteVectorStore
    ) -> None:
        store.add([_make_chunk("keep", chunk_index=0)])
        assert store.delete_material("nope") == 0
        assert store.count() == 1

    def test_delete_only_removes_target_material_across_owners(
        self, store: SqliteVectorStore
    ) -> None:
        store.add(
            [
                _make_chunk("alice", uploaded_by="alice", material_id="mat-1", chunk_index=0),
                _make_chunk("alice2", uploaded_by="alice", material_id="mat-1", chunk_index=1),
                _make_chunk("bob", uploaded_by="bob", material_id="mat-2", chunk_index=0),
            ]
        )
        assert store.delete_material("mat-1") == 2
        assert store.count() == 1
        texts = [r.text for r in store.search(AXIS[0], SearchFilter(user_id="bob"))]
        assert texts == ["bob"]


class TestPersistence:
    def test_data_survives_close_and_reopen(
        self, store_path: Path
    ) -> None:
        first = SqliteVectorStore(store_path)
        first.add(
            [
                _make_chunk("one", chunk_index=0),
                _make_chunk("two", chunk_index=1, embedding=AXIS[1]),
            ]
        )
        first.close()

        second = SqliteVectorStore(store_path)
        try:
            assert second.count() == 2
            assert second.dimension == 4
            results = second.search(AXIS[1], SearchFilter(user_id="user-1"))
            assert results[0].chunk_id == "mat-1:1"
        finally:
            second.close()

    def test_file_is_written_to_disk(self, store_path: Path) -> None:
        store = SqliteVectorStore(store_path)
        store.add([_make_chunk("one", chunk_index=0)])
        store.close()
        assert store_path.exists()
        assert store_path.stat().st_size > 0


class TestCorruption:
    def test_corrupt_embedding_blob_detected(self, store: SqliteVectorStore, store_path: Path) -> None:
        store.add(
            [
                _make_chunk("healthy", uploaded_by="alice", material_id="m1", chunk_index=0),
                _make_chunk("breakme", uploaded_by="alice", material_id="m2", chunk_index=0),
            ]
        )
        conn = sqlite3.connect(str(store_path))
        conn.execute("UPDATE chunks SET embedding = ? WHERE material_id = ?", (b"\x00\x01", "m2"))
        conn.commit()
        conn.close()

        with pytest.raises(VectorStoreCorruptedError):
            store.search(AXIS[0], SearchFilter(user_id="alice"))

    def test_corrupt_dimension_record_detected_on_open(self, store_path: Path) -> None:
        store = SqliteVectorStore(store_path)
        store.add([_make_chunk("seed", chunk_index=0)])
        store.close()

        conn = sqlite3.connect(str(store_path))
        conn.execute(
            "INSERT OR REPLACE INTO store_meta (key, value) VALUES (?, ?)",
            ("embedding_dimension", "not-an-int"),
        )
        conn.commit()
        conn.close()

        with pytest.raises(VectorStoreCorruptedError):
            SqliteVectorStore(store_path)

    def test_used_after_close_raises(self, store: SqliteVectorStore) -> None:
        store.close()
        with pytest.raises(VectorStoreUnavailableError):
            store.count()

    def test_close_is_idempotent(self, store: SqliteVectorStore) -> None:
        store.close()
        store.close()  # must not raise


class TestDimensionCompatibility:
    def test_reopen_keeps_dimension_contract(self, store_path: Path) -> None:
        first = SqliteVectorStore(store_path)
        first.add([_make_chunk("seed", chunk_index=0, embedding=AXIS[0])])
        first.close()

        second = SqliteVectorStore(store_path)
        try:
            assert second.dimension == 4
        finally:
            second.close()