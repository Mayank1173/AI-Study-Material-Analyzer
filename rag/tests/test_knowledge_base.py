"""Integration tests for the KnowledgeBase service (indexing + search)."""

from __future__ import annotations

from pathlib import Path

import pytest

from rag.embeddings import DeterministicEmbedder
from rag.errors import (
    EmptyQueryError,
    IndexingError,
)
from rag.knowledge_base import KnowledgeBase
from rag.models import ProcessedDocument, SourceRef
from rag.vectorstore import SqliteVectorStore

PHOTOSYNTHESIS_TEXT = (
    "Photosynthesis converts light energy into chemical energy. "
    "The light-dependent reactions occur in the thylakoid membrane. "
    "The Calvin cycle fixes carbon dioxide into glucose in the stroma."
)
OS_TEXT = (
    "Operating systems schedule processes. "
    "Round-robin scheduling gives each fixed time slices. "
    "The ready queue holds all runnable processes."
)
ALGEBRA_TEXT = (
    "Linear algebra studies vectors and matrices. "
    "A matrix represents a linear transformation between vector spaces."
)


@pytest.fixture()
def embedder() -> DeterministicEmbedder:
    return DeterministicEmbedder(dimension=64)


@pytest.fixture()
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "kb.db"


@pytest.fixture()
def knowledge_base(embedder: DeterministicEmbedder, store_path: Path) -> KnowledgeBase:
    kb = KnowledgeBase(embedder, SqliteVectorStore(str(store_path)))
    yield kb
    kb.close()


def _write_topic_file(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _topic_file(tmp_path: Path) -> Path:
    return _write_topic_file(
        tmp_path,
        "notes.txt",
        f"{PHOTOSYNTHESIS_TEXT}\n\n{ALGEBRA_TEXT}\n\n{OS_TEXT}",
    )


class TestIndexing:
    def test_index_material_returns_chunk_count(
        self,
        knowledge_base: KnowledgeBase,
        tmp_path: Path,
    ) -> None:
        count = knowledge_base.index_material(
            _topic_file(tmp_path),
            source_ref=SourceRef(material_id="m1", course_id="c1"),
            uploaded_by="alice",
        )
        assert count >= 1
        assert knowledge_base.count(user_id="alice") == count

    def test_index_processed_returns_zero_for_empty_document(
        self, knowledge_base: KnowledgeBase
    ) -> None:
        document = ProcessedDocument(
            source=SourceRef(material_id="m1", course_id="c1"),
            file_type=".txt",
            extracted_text="",
            chunks=(),
            total_chunks=0,
        )
        assert (
            knowledge_base.index_processed(document, uploaded_by="alice") == 0
        )

    def test_missing_material_id_rejected(
        self,
        knowledge_base: KnowledgeBase,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(IndexingError):
            knowledge_base.index_material(
                _topic_file(tmp_path),
                source_ref=SourceRef(course_id="c1"),
                uploaded_by="alice",
            )

    def test_missing_uploaded_by_rejected(
        self,
        knowledge_base: KnowledgeBase,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(IndexingError):
            knowledge_base.index_material(
                _topic_file(tmp_path),
                source_ref=SourceRef(material_id="m1", course_id="c1"),
                uploaded_by="",
            )

    def test_reindex_replaces_without_duplicates(
        self,
        knowledge_base: KnowledgeBase,
        tmp_path: Path,
    ) -> None:
        path = _topic_file(tmp_path)
        first = knowledge_base.index_material(
            path,
            source_ref=SourceRef(material_id="m1", course_id="c1"),
            uploaded_by="alice",
        )
        second = knowledge_base.index_material(
            path,
            source_ref=SourceRef(material_id="m1", course_id="c1"),
            uploaded_by="alice",
        )
        assert first == second
        assert knowledge_base.count(user_id="alice") == first

    def test_chunk_ids_are_stable_and_unique(
        self,
        knowledge_base: KnowledgeBase,
        tmp_path: Path,
    ) -> None:
        count = knowledge_base.index_material(
            _topic_file(tmp_path),
            source_ref=SourceRef(material_id="m1", course_id="c1"),
            uploaded_by="alice",
        )
        results = knowledge_base.search(
            "scheduling",
            user_id="alice",
            top_k=count,
        )
        chunk_ids = [r.chunk_id for r in results]
        assert all(cid.startswith("m1:") for cid in chunk_ids)
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_delete_material_removes_chunks(
        self,
        knowledge_base: KnowledgeBase,
        tmp_path: Path,
    ) -> None:
        knowledge_base.index_material(
            _topic_file(tmp_path),
            source_ref=SourceRef(material_id="m1", course_id="c1"),
            uploaded_by="alice",
        )
        assert knowledge_base.count(user_id="alice") > 0
        assert knowledge_base.delete_material("m1") > 0
        assert knowledge_base.count(user_id="alice") == 0

    def test_delete_missing_material_returns_zero(
        self, knowledge_base: KnowledgeBase
    ) -> None:
        assert knowledge_base.delete_material("nope") == 0


class TestSearch:
    def test_relevant_topic_ranks_first(
        self,
        knowledge_base: KnowledgeBase,
        tmp_path: Path,
    ) -> None:
        _write_topic_file(
            tmp_path, "os.txt", OS_TEXT
        )
        _write_topic_file(
            tmp_path, "photo.txt", PHOTOSYNTHESIS_TEXT
        )
        knowledge_base.index_material(
            tmp_path / "os.txt",
            source_ref=SourceRef(material_id="m-os", course_id="c1"),
            uploaded_by="alice",
        )
        knowledge_base.index_material(
            tmp_path / "photo.txt",
            source_ref=SourceRef(material_id="m-photo", course_id="c1"),
            uploaded_by="alice",
        )

        results = knowledge_base.search("carbon dioxide fixation", user_id="alice")
        assert results
        assert results[0].material_id == "m-photo"
        assert results[0].score > 0.0

    def test_document_metadata_is_returned(
        self,
        knowledge_base: KnowledgeBase,
        tmp_path: Path,
    ) -> None:
        path = _write_topic_file(tmp_path, "photo.txt", PHOTOSYNTHESIS_TEXT)
        knowledge_base.index_material(
            path,
            source_ref=SourceRef(
                material_id="m1",
                course_id="c1",
                original_filename=path.name,
                material_title="Photosynthesis Notes",
            ),
            uploaded_by="alice",
        )
        results = knowledge_base.search("photosynthesis", user_id="alice")
        assert results[0].metadata.material_title == "Photosynthesis Notes"
        assert results[0].metadata.material_id == "m1"
        assert results[0].metadata.course_id == "c1"

    def test_empty_query_rejected(self, knowledge_base: KnowledgeBase) -> None:
        with pytest.raises(EmptyQueryError):
            knowledge_base.search("  ", user_id="alice")

    def test_blank_query_rejected(self, knowledge_base: KnowledgeBase) -> None:
        with pytest.raises(EmptyQueryError):
            knowledge_base.search("", user_id="alice")

    def test_owner_filter_isolates_users(
        self,
        knowledge_base: KnowledgeBase,
        tmp_path: Path,
    ) -> None:
        _write_topic_file(tmp_path, "photo.txt", PHOTOSYNTHESIS_TEXT)
        _write_topic_file(tmp_path, "os.txt", OS_TEXT)
        knowledge_base.index_material(
            tmp_path / "photo.txt",
            source_ref=SourceRef(material_id="m1", course_id="c1"),
            uploaded_by="alice",
        )
        knowledge_base.index_material(
            tmp_path / "os.txt",
            source_ref=SourceRef(material_id="m2", course_id="c1"),
            uploaded_by="bob",
        )
        assert knowledge_base.search("photosynthesis", user_id="alice", top_k=5)[0].material_id == "m1"
        assert knowledge_base.search("photosynthesis", user_id="bob", top_k=5)[0].material_id == "m2"

    def test_empty_results_when_owner_has_nothing(
        self,
        knowledge_base: KnowledgeBase,
        tmp_path: Path,
    ) -> None:
        _write_topic_file(tmp_path, "photo.txt", PHOTOSYNTHESIS_TEXT)
        knowledge_base.index_material(
            tmp_path / "photo.txt",
            source_ref=SourceRef(material_id="m1", course_id="c1"),
            uploaded_by="alice",
        )
        assert knowledge_base.search("anything", user_id="carol") == []

    def test_course_filter_narrows_results(
        self,
        knowledge_base: KnowledgeBase,
        tmp_path: Path,
    ) -> None:
        _write_topic_file(tmp_path, "photo.txt", PHOTOSYNTHESIS_TEXT)
        _write_topic_file(tmp_path, "os.txt", OS_TEXT)
        knowledge_base.index_material(
            tmp_path / "photo.txt",
            source_ref=SourceRef(material_id="m1", course_id="c1"),
            uploaded_by="alice",
        )
        knowledge_base.index_material(
            tmp_path / "os.txt",
            source_ref=SourceRef(material_id="m2", course_id="c2"),
            uploaded_by="alice",
        )
        results = knowledge_base.search(
            "scheduling", user_id="alice", course_id="c2", top_k=5
        )
        assert {r.material_id for r in results} == {"m2"}

    def test_material_filter_narrows_results(
        self,
        knowledge_base: KnowledgeBase,
        tmp_path: Path,
    ) -> None:
        _write_topic_file(tmp_path, "os.txt", OS_TEXT)
        knowledge_base.index_material(
            tmp_path / "os.txt",
            source_ref=SourceRef(material_id="m1", course_id="c1"),
            uploaded_by="alice",
        )
        assert (
            knowledge_base.search(
                "round robin", user_id="alice", material_id="m1", top_k=5
            )
            != []
        )
        assert (
            knowledge_base.search(
                "round robin", user_id="alice", material_id="m-other", top_k=5
            )
            == []
        )

    def test_empty_user_id_rejected(
        self,
        knowledge_base: KnowledgeBase,
        tmp_path: Path,
    ) -> None:
        _write_topic_file(tmp_path, "os.txt", OS_TEXT)
        knowledge_base.index_material(
            tmp_path / "os.txt",
            source_ref=SourceRef(material_id="m1", course_id="c1"),
            uploaded_by="alice",
        )
        with pytest.raises(ValueError):
            knowledge_base.search("round robin", user_id="")


class TestPersistence:
    def test_knowledge_base_survives_reopen(
        self, embedder: DeterministicEmbedder, store_path: Path, tmp_path: Path
    ) -> None:
        _write_topic_file(tmp_path, "os.txt", OS_TEXT)
        first = KnowledgeBase(embedder, SqliteVectorStore(str(store_path)))
        first.index_material(
            tmp_path / "os.txt",
            source_ref=SourceRef(material_id="m1", course_id="c1"),
            uploaded_by="alice",
        )
        first.close()

        second = KnowledgeBase(embedder, SqliteVectorStore(str(store_path)))
        try:
            assert second.count(user_id="alice") > 0
            results = second.search("round robin scheduling", user_id="alice")
            assert results and results[0].material_id == "m1"
        finally:
            second.close()


class TestCountScoping:
    def test_global_count_and_per_user_count(
        self,
        knowledge_base: KnowledgeBase,
        tmp_path: Path,
    ) -> None:
        _write_topic_file(tmp_path, "photo.txt", PHOTOSYNTHESIS_TEXT)
        _write_topic_file(tmp_path, "os.txt", OS_TEXT)
        knowledge_base.index_material(
            tmp_path / "photo.txt",
            source_ref=SourceRef(material_id="m1", course_id="c1"),
            uploaded_by="alice",
        )
        knowledge_base.index_material(
            tmp_path / "os.txt",
            source_ref=SourceRef(material_id="m2", course_id="c1"),
            uploaded_by="bob",
        )
        global_count = knowledge_base.count()
        assert knowledge_base.count(user_id="alice") + knowledge_base.count(user_id="bob") == global_count
        assert knowledge_base.count(user_id="alice", course_id="c1") == knowledge_base.count(user_id="alice")