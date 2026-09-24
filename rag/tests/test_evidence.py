"""Tests for the multi-source evidence collection layer (Phase 2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from rag.embeddings import DeterministicEmbedder
from rag.evidence import (
    MAX_CHUNKS_PER_MATERIAL,
    canonical_text,
    collect_evidence,
    deduplicate_results,
    diversify_by_material,
    group_by_material,
)
from rag.knowledge_base import KnowledgeBase
from rag.models import ChunkMetadata, SearchResult, SourceRef
from rag.vectorstore import SqliteVectorStore

NOTES_TEXT = (
    "Deadlock prevention breaks the circular wait condition to stop deadlocks "
    "before they occur. Deadlock prevention ensures every resource is "
    "requested in a fixed global order. Deadlock prevention forbids holding "
    "one resource while waiting for another. Deadlock prevention requires "
    "processes to request all needed resources at once. Deadlock prevention "
    "never allows a process to wait once it holds a resource."
)
PPT_TEXT = (
    "Deadlock avoidance uses the banker's algorithm to check every allocation "
    "for safety. Deadlock avoidance permits a request only when the system "
    "stays in a safe state. Deadlock avoidance replays each future claim to "
    "prevent deadlock before it occurs."
)
ALGEBRA_TEXT = (
    "Linear algebra studies vectors and matrices. A matrix represents a "
    "linear transformation between vector spaces."
)


def _make_result(
    text: str,
    material_id: str = "m1",
    course_id: str = "c1",
    score: float = 0.8,
    source_location: str | None = None,
) -> SearchResult:
    return SearchResult(
        chunk_id=f"{material_id}:0",
        material_id=material_id,
        course_id=course_id,
        uploaded_by="alice",
        text=text,
        score=score,
        metadata=ChunkMetadata(
            material_id=material_id,
            course_id=course_id,
            original_filename="notes.pdf",
            material_title="Notes",
            source_type=".pdf",
            chunk_index=0,
            total_chunks=1,
            source_location=source_location,
        ),
    )


class TestCanonicalText:
    def test_normalizes_whitespace_and_case(self) -> None:
        assert canonical_text("  Deadlock\n\n Prevention ") == "deadlock prevention"

    def test_empty_and_blank(self) -> None:
        assert canonical_text("") == ""
        assert canonical_text("   ") == ""


class TestDeduplicateResults:
    def test_keeps_top_scoring_copy_within_material(self) -> None:
        results = [
            _make_result("Deadlock prevention", score=0.9),
            _make_result("Deadlock prevention", score=0.8),
        ]
        deduped = deduplicate_results(results)
        assert len(deduped) == 1
        assert deduped[0].score == 0.9

    def test_keeps_distinct_texts_in_same_material(self) -> None:
        results = [
            _make_result("Deadlock prevention", score=0.9),
            _make_result("Deadlock avoidance", score=0.8),
        ]
        assert len(deduplicate_results(results)) == 2

    def test_keeps_identical_texts_from_different_materials(self) -> None:
        results = [
            _make_result("Shared text", material_id="m1", score=0.9),
            _make_result("Shared text", material_id="m2", score=0.8),
        ]
        deduped = deduplicate_results(results)
        assert len(deduped) == 2
        assert {r.material_id for r in deduped} == {"m1", "m2"}

    def test_normalization_is_case_and_whitespace_insensitive(self) -> None:
        results = [
            _make_result("Deadlock  prevention", score=0.9),
            _make_result("deadlock prevention", score=0.7),
            _make_result("deadlock prevention ", score=0.5),
        ]
        assert len(deduplicate_results(results)) == 1


class TestDiversifyByMaterial:
    def test_caps_single_material_share(self) -> None:
        results = [
            _make_result(f"chunk {i}", material_id="m1", score=1.0 - i * 0.05)
            for i in range(5)
        ]
        diversified = diversify_by_material(results, per_material_cap=3)
        assert len(diversified) == 3

    def test_preserves_relevance_order(self) -> None:
        scores = [0.95, 0.9, 0.85, 0.8, 0.75]
        results = [
            _make_result(f"chunk {i}", material_id="m1", score=scores[i])
            for i in range(5)
        ]
        diversified = diversify_by_material(results, per_material_cap=3)
        assert [r.score for r in diversified] == scores[:3]

    def test_second_material_fills_remaining_slots(self) -> None:
        results = [
            _make_result("notes 1", material_id="m-notes", score=0.95),
            _make_result("notes 2", material_id="m-notes", score=0.94),
            _make_result("notes 3", material_id="m-notes", score=0.93),
            _make_result("notes 4", material_id="m-notes", score=0.92),
            _make_result("ppt 1", material_id="m-ppt", score=0.9),
            _make_result("ppt 2", material_id="m-ppt", score=0.89),
        ]
        diversified = diversify_by_material(results, per_material_cap=3)
        material_counts: dict[str, int] = {}
        for result in diversified:
            material_counts[result.material_id] = (
                material_counts.get(result.material_id, 0) + 1
            )
        assert material_counts["m-notes"] == 3
        assert material_counts["m-ppt"] == 2
        assert [r.score for r in diversified] == [0.95, 0.94, 0.93, 0.9, 0.89]

    def test_rejects_zero_cap(self) -> None:
        with pytest.raises(ValueError):
            diversify_by_material([_make_result("x")], per_material_cap=0)


class TestGroupByMaterial:
    def test_groups_non_contiguous_runs(self) -> None:
        a1 = _make_result("a one", material_id="m1")
        b1 = _make_result("b one", material_id="m2")
        a2 = _make_result("a two", material_id="m1")
        grouped = group_by_material([a1, b1, a2])
        assert [r.text for r in grouped] == ["a one", "a two", "b one"]

    def test_preserves_within_material_order(self) -> None:
        a1 = _make_result("a1", material_id="m1", score=0.9)
        a2 = _make_result("a2", material_id="m1", score=0.7)
        b1 = _make_result("b1", material_id="m2", score=0.95)
        grouped = group_by_material([a1, b1, a2])
        assert [r.text for r in grouped] == ["a1", "a2", "b1"]


@pytest.fixture()
def embedder() -> DeterministicEmbedder:
    return DeterministicEmbedder(dimension=64)


@pytest.fixture()
def kb(embedder: DeterministicEmbedder, tmp_path: Path) -> KnowledgeBase:
    base = KnowledgeBase(embedder, SqliteVectorStore(str(tmp_path / "evidence.db")))
    yield base
    base.close()


def _index(
    kb: KnowledgeBase,
    tmp_path: Path,
    *,
    name: str,
    text: str,
    material_id: str,
    course_id: str,
    title: str,
    filename: str,
    user: str = "alice",
    chunk_size: int = 120,
    overlap: int = 20,
) -> None:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    kb.index_material(
        path,
        source_ref=SourceRef(
            material_id=material_id,
            course_id=course_id,
            original_filename=filename,
            material_title=title,
        ),
        uploaded_by=user,
        chunk_size=chunk_size,
        overlap=overlap,
    )


def _index_notes(kb: KnowledgeBase, tmp_path: Path, user: str = "alice") -> None:
    _index(
        kb,
        tmp_path,
        name="notes.txt",
        text=NOTES_TEXT,
        material_id="m-notes",
        course_id="c-os",
        title="OS Notes",
        filename="OS Notes.pdf",
        user=user,
    )


def _index_ppt(kb: KnowledgeBase, tmp_path: Path, user: str = "alice") -> None:
    _index(
        kb,
        tmp_path,
        name="ppt.txt",
        text=PPT_TEXT,
        material_id="m-ppt",
        course_id="c-os",
        title="OS Lecture PPT",
        filename="OS Lecture PPT.pptx",
        user=user,
    )


class TestCollectEvidenceSingleSource:
    def test_single_material_query(self, kb: KnowledgeBase, tmp_path: Path) -> None:
        _index_notes(kb, tmp_path)
        evidence = collect_evidence(
            kb, query="deadlock prevention", user_id="alice", max_evidence=3
        )
        assert evidence
        assert all(r.material_id == "m-notes" for r in evidence)
        assert len(evidence) <= 3

    def test_source_metadata_retained(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_notes(kb, tmp_path)
        evidence = collect_evidence(
            kb, query="deadlock prevention", user_id="alice"
        )
        assert evidence
        result = evidence[0]
        assert result.material_id == "m-notes"
        assert result.course_id == "c-os"
        assert result.score > 0.0
        assert result.metadata.material_title == "OS Notes"
        assert result.metadata.original_filename == "OS Notes.pdf"
        assert result.metadata.source_type == ".txt"
        assert result.metadata.total_chunks == 5


class TestCollectEvidenceMultiSource:
    def test_retrieves_evidence_from_multiple_materials(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_notes(kb, tmp_path)
        _index_ppt(kb, tmp_path)
        evidence = collect_evidence(
            kb, query="deadlock prevention and avoidance", user_id="alice"
        )
        assert evidence
        assert len(evidence) <= 3
        assert len(evidence) >= 2
        materials = {r.material_id for r in evidence}
        assert "m-notes" in materials
        assert "m-ppt" in materials

    def test_grouped_within_material_order(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_notes(kb, tmp_path)
        _index_ppt(kb, tmp_path)
        evidence = collect_evidence(
            kb, query="deadlock", user_id="alice", max_evidence=6
        )
        runs = [r.material_id for r in evidence]
        # every material's chunks appear in a single contiguous block
        material_runs: dict[str, int] = {}
        previous: str | None = None
        for material_id in runs:
            if material_id != previous:
                material_runs[material_id] = material_runs.get(material_id, 0) + 1
            previous = material_id
        assert all(count == 1 for count in material_runs.values())


class TestCollectEvidenceDiversity:
    def test_no_single_material_dominates(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_notes(kb, tmp_path)
        _index_ppt(kb, tmp_path)
        evidence = collect_evidence(
            kb, query="deadlock prevention and avoidance", user_id="alice",
            max_evidence=6,
        )
        notes_count = sum(1 for r in evidence if r.material_id == "m-notes")
        ppt_count = sum(1 for r in evidence if r.material_id == "m-ppt")
        assert len(evidence) == 6
        assert notes_count <= MAX_CHUNKS_PER_MATERIAL
        assert ppt_count >= 1

    def test_relevance_remains_primary_ranking_factor(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_notes(kb, tmp_path)
        _index_ppt(kb, tmp_path)
        evidence = collect_evidence(
            kb, query="deadlock prevention and avoidance", user_id="alice",
            max_evidence=6,
        )
        assert evidence[0].score >= evidence[-1].score
        # every evidence item is one of the retrieved candidates, never invented
        assert all(r.material_id in {"m-notes", "m-ppt"} for r in evidence)

    def test_irrelevant_material_not_elevated_above_relevant(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_notes(kb, tmp_path)
        _index_ppt(kb, tmp_path)
        _index(
            kb,
            tmp_path,
            name="algebra.txt",
            text=ALGEBRA_TEXT,
            material_id="m-algebra",
            course_id="c-math",
            title="Algebra",
            filename="algebra.txt",
            user="alice",
        )
        evidence = collect_evidence(
            kb,
            query="deadlock prevention and avoidance",
            user_id="alice",
            max_evidence=3,
            candidate_pool=3,
        )
        # With a tight candidate pool the irrelevant material must not push out
        # the clearly relevant notes/ppt chunks.
        assert all(r.material_id in {"m-notes", "m-ppt"} for r in evidence)


class TestCollectEvidenceScoping:
    def test_course_filter(self, kb: KnowledgeBase, tmp_path: Path) -> None:
        _index_notes(kb, tmp_path)
        _index_ppt(kb, tmp_path)
        _index(
            kb,
            tmp_path,
            name="alg.txt",
            text=ALGEBRA_TEXT,
            material_id="m-algebra",
            course_id="c-math",
            title="Algebra",
            filename="algebra.txt",
            user="alice",
        )
        evidence = collect_evidence(
            kb, query="deadlock", user_id="alice", course_id="c-os",
            max_evidence=10, candidate_pool=10,
        )
        assert evidence
        assert all(r.course_id == "c-os" for r in evidence)

    def test_material_filter(self, kb: KnowledgeBase, tmp_path: Path) -> None:
        _index_notes(kb, tmp_path)
        _index_ppt(kb, tmp_path)
        evidence = collect_evidence(
            kb, query="deadlock", user_id="alice", material_id="m-ppt",
            max_evidence=10, candidate_pool=10,
        )
        assert evidence
        assert all(r.material_id == "m-ppt" for r in evidence)

    def test_ownership_isolation(self, kb: KnowledgeBase, tmp_path: Path) -> None:
        _index_notes(kb, tmp_path, user="alice")
        evidence = collect_evidence(
            kb, query="deadlock prevention", user_id="bob"
        )
        assert evidence == []

    def test_no_context_when_owner_has_nothing(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_notes(kb, tmp_path, user="alice")
        assert collect_evidence(kb, query="anything", user_id="carol") == []

    def test_max_evidence_respected(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_notes(kb, tmp_path)
        _index_ppt(kb, tmp_path)
        evidence = collect_evidence(
            kb, query="deadlock", user_id="alice", max_evidence=2,
            candidate_pool=10,
        )
        assert len(evidence) == 2

    def test_zero_max_evidence(self, kb: KnowledgeBase, tmp_path: Path) -> None:
        _index_notes(kb, tmp_path)
        assert collect_evidence(
            kb, query="deadlock", user_id="alice", max_evidence=0
        ) == []

    def test_blank_query(self, kb: KnowledgeBase, tmp_path: Path) -> None:
        _index_notes(kb, tmp_path)
        assert collect_evidence(kb, query="   ", user_id="alice") == []