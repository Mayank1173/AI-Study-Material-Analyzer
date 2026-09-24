"""Phase 4 tests: advanced source reasoning.

Covers source-aware attribution, multi-source synthesis, conflict-aware
reasoning, missing-information protection, per-intent grounding, and the
guarantee that cited [Source N] numbers always line up with the retrieved
evidence (never invented, never from outside the material).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rag.answer import answer_question
from rag.context_builder import (
    CONTEXT_DELIMITER_END,
    CONTEXT_DELIMITER_START,
    INTENT_SYSTEM_PROMPTS,
    NO_CONTEXT_SYSTEM_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_grounded_prompt,
    build_summary_prompt,
)
from rag.conversation import ConversationTurn
from rag.embeddings import DeterministicEmbedder
from rag.evidence import collect_evidence, source_kind
from rag.intent import (
    INTENT_COMPARISON,
    INTENT_EXAM,
    INTENT_EXPLANATION,
    INTENT_SIMPLE,
    INTENT_SUMMARY,
)
from rag.knowledge_base import KnowledgeBase
from rag.llm.mock_provider import MockProvider
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
    material_title: str | None = "Test Material",
    original_filename: str | None = "test.pdf",
    source_location: str | None = "Page 1",
    score: float = 0.9,
    source_type: str = ".pdf",
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
            original_filename=original_filename,
            material_title=material_title,
            source_type=source_type,
            chunk_index=0,
            total_chunks=1,
            source_location=source_location,
        ),
    )


@pytest.fixture()
def embedder() -> DeterministicEmbedder:
    return DeterministicEmbedder(dimension=64)


@pytest.fixture()
def kb(embedder: DeterministicEmbedder, tmp_path: Path) -> KnowledgeBase:
    base = KnowledgeBase(embedder, SqliteVectorStore(str(tmp_path / "p4.db")))
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
        name="os-notes.txt",
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
        name="os-ppt.txt",
        text=PPT_TEXT,
        material_id="m-ppt",
        course_id="c-os",
        title="OS Slides",
        filename="OS Slides.pptx",
        user=user,
    )


def _citations(prompt: str) -> str:
    prefix = "Available source numbers for citations:"
    start = prompt.index(prefix) + len(prefix)
    end = prompt.index(".", start)
    return prompt[start:end].strip()


class TestSourceKind:
    """Descriptive source kind is derived from filename + extension."""

    def test_notes_keyword_wins(self) -> None:
        meta = ChunkMetadata(
            material_id="m",
            course_id="c",
            original_filename="study notes.pdf",
            material_title=None,
            source_type=".pdf",
            chunk_index=0,
            total_chunks=1,
        )
        assert source_kind(meta) == "Notes"

    def test_previous_year_paper_keyword(self) -> None:
        meta = ChunkMetadata(
            material_id="m",
            course_id="c",
            original_filename="PYQ 2021.pdf",
            material_title=None,
            source_type=".pdf",
            chunk_index=0,
            total_chunks=1,
        )
        assert source_kind(meta) == "Previous-year paper"

    def test_question_bank_keyword(self) -> None:
        meta = ChunkMetadata(
            material_id="m",
            course_id="c",
            original_filename="Question Bank.docx",
            material_title=None,
            source_type=".docx",
            chunk_index=0,
            total_chunks=1,
        )
        assert source_kind(meta) == "Question bank"

    def test_extension_fallback(self) -> None:
        meta = ChunkMetadata(
            material_id="m",
            course_id="c",
            original_filename="lecture.pptx",
            material_title=None,
            source_type=".pptx",
            chunk_index=0,
            total_chunks=1,
        )
        assert source_kind(meta) == "Presentation"

    def test_unknown_extension_default(self) -> None:
        meta = ChunkMetadata(
            material_id="m",
            course_id="c",
            original_filename="lecture.xyz",
            material_title=None,
            source_type=".xyz",
            chunk_index=0,
            total_chunks=1,
        )
        assert source_kind(meta) == "Study material"


class TestSourceAttribution:
    """[Source N] labels carry material, location, and type."""

    def test_label_includes_material_location_type(self) -> None:
        result = _make_result(
            "DNA stores genetic information.",
            material_title="Bio Notes",
            original_filename="Bio Deck.pptx",
            source_location="Slide 3",
            source_type=".pptx",
        )
        _, user = build_grounded_prompt("What is DNA?", [result])
        block = user[user.index(CONTEXT_DELIMITER_START): user.index(CONTEXT_DELIMITER_END)]
        assert "Material: Bio Notes" in block
        assert "Location: Slide 3" in block
        assert "Type: Presentation" in block

    def test_label_falls_back_to_filename(self) -> None:
        result = _make_result(
            "text", material_title=None, original_filename="notes.txt", source_type=".txt"
        )
        _, user = build_grounded_prompt("q", [result])
        block = user[user.index(CONTEXT_DELIMITER_START): user.index(CONTEXT_DELIMITER_END)]
        assert "Material: notes.txt" in block

    def test_two_sources_numbered_and_grouped(self) -> None:
        r1 = _make_result("a", material_id="m1", material_title="Doc A")
        r2 = _make_result("b", material_id="m2", material_title="Doc B")
        system, user = build_grounded_prompt("q", [r1, r2])
        assert system == SYSTEM_PROMPT
        assert user.index("SOURCE A:") < user.index("SOURCE B:")
        assert user.find("[Source 1]") < user.find("[Source 2]")
        assert "Doc A" in user and "Doc B" in user

    def test_citation_list_matches_evidence_count(self) -> None:
        r1 = _make_result("one", material_id="m1")
        r2 = _make_result("two", material_id="m2")
        r3 = _make_result("three", material_id="m3")
        _, user = build_grounded_prompt("q", [r1, r2, r3])
        assert _citations(user) == "[Source 1] [Source 2] [Source 3]"
        assert "[Source 4]" not in user

    def test_no_context_has_no_invented_sources(self) -> None:
        system, user = build_grounded_prompt("q", [])
        assert system == NO_CONTEXT_SYSTEM_PROMPT
        assert "[Source" not in user

    def test_summary_prompt_also_lists_real_sources(self) -> None:
        r1 = _make_result("one", material_id="m1")
        r2 = _make_result("two", material_id="m2")
        _, user = build_summary_prompt("OS", [r1, r2])
        assert _citations(user) == "[Source 1] [Source 2]"


class TestSourceSynthesis:
    """Several sources combine; irrelevant material is excluded."""

    def test_two_sources_both_contribute(self) -> None:
        r1 = _make_result("Deadlock prevention.", material_id="m1")
        r2 = _make_result("Deadlock avoidance.", material_id="m2")
        _, user = build_grounded_prompt("Compare them.", [r1, r2])
        assert "Deadlock prevention." in user
        assert "Deadlock avoidance." in user

    def test_three_sources_all_present(self) -> None:
        results = [
            _make_result(f"chunk {i}", material_id=f"m{i}")
            for i in (1, 2, 3)
        ]
        _, user = build_grounded_prompt("q", results)
        for i in (1, 2, 3):
            assert f"chunk {i}" in user

    def test_irrelevant_ranked_tail_excluded_by_stub_kb(self) -> None:
        class _FakeKB:
            def search(self, query, *, user_id, course_id=None, material_id=None, top_k):
                return [
                    _make_result("relevant one", material_id="m1", score=0.95),
                    _make_result("relevant two", material_id="m2", score=0.9),
                    _make_result("irrelevant topic", material_id="m3", score=0.1),
                ]

        evidence = collect_evidence(
            _FakeKB(), query="deadlock", user_id="alice", max_evidence=2
        )
        assert [r.material_id for r in evidence] == ["m1", "m2"]
        _, user = build_grounded_prompt("deadlock", evidence)
        assert "irrelevant topic" not in user
        assert _citations(user) == "[Source 1] [Source 2]"

    def test_irrelevant_material_not_elevated_in_real_kb(
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
        )
        evidence = collect_evidence(
            kb,
            query="deadlock prevention and avoidance",
            user_id="alice",
            max_evidence=3,
            candidate_pool=3,
        )
        assert evidence
        assert all(r.material_id in {"m-notes", "m-ppt"} for r in evidence)
        _, user = build_grounded_prompt("deadlock prevention and avoidance", evidence)
        assert "linear algebra" not in user.lower()

    def test_duplicate_facts_from_distinct_materials_both_kept(self) -> None:
        a = _make_result("Shared fact about the kernel.", material_id="m1")
        b = _make_result("Shared fact about the kernel.", material_id="m2")
        _, user = build_grounded_prompt("kernel", [a, b])
        assert "[Source 1]" in user
        assert "[Source 2]" in user


class TestConflictAwareReasoning:
    """Conflicting claims are presented per source, never silently resolved."""

    def test_conflict_instructions_in_general_prompt(self) -> None:
        lower = SYSTEM_PROMPT.lower()
        assert "do not silently choose one as correct" in lower
        assert "do not silently pick one as correct" in lower
        assert "authoritative" in lower
        assert "never use outside knowledge to decide which source is right" in lower
        assert "state that the materials differ" in lower

    def test_conflict_instructions_in_summary_prompt(self) -> None:
        lower = SUMMARY_SYSTEM_PROMPT.lower()
        assert "conflicting" in lower
        assert "do not silently choose one as correct" in lower
        assert "never use outside knowledge to resolve disagreements" in lower

    def test_conflicting_claims_both_presented_with_labels(self) -> None:
        r1 = _make_result(
            "Deadlock prevention is used and breaks circular wait.",
            material_id="m-notes",
            material_title="OS Notes",
        )
        r2 = _make_result(
            "Deadlock prevention is not used; avoidance is used instead.",
            material_id="m-ppt",
            material_title="OS Slides",
        )
        system, user = build_grounded_prompt("How is deadlock prevented?", [r1, r2])
        assert "Deadlock prevention is used" in user
        assert "Deadlock prevention is not used" in user
        assert "OS Notes" in user
        assert "OS Slides" in user
        assert "do not silently choose one as correct" in system.lower()

    def test_exam_intent_wont_hide_conflict(self) -> None:
        lower = INTENT_SYSTEM_PROMPTS[INTENT_EXAM].lower()
        assert "conflicting" in lower
        assert "present the conflicting statements" in lower
        assert "outside the retrieved material" in lower

    def test_pipeline_preserves_conflicting_evidence(self, tmp_path) -> None:
        path_notes = tmp_path / "os-notes.txt"
        path_notes.write_text(
            "Deadlock prevention breaks the circular wait condition.",
            encoding="utf-8",
        )
        path_ppt = tmp_path / "os-ppt.txt"
        path_ppt.write_text(
            "Deadlock prevention is not used; avoidance is used instead.",
            encoding="utf-8",
        )
        kb = KnowledgeBase(
            DeterministicEmbedder(dimension=64),
            SqliteVectorStore(str(tmp_path / "kb.db")),
        )
        kb.index_material(
            path_notes,
            source_ref=SourceRef(
                material_id="m-notes",
                course_id="c-os",
                original_filename="os-notes.txt",
                material_title="OS Notes",
            ),
            uploaded_by="alice",
        )
        kb.index_material(
            path_ppt,
            source_ref=SourceRef(
                material_id="m-ppt",
                course_id="c-os",
                original_filename="os-ppt.txt",
                material_title="OS Slides",
            ),
            uploaded_by="alice",
        )
        llm = MockProvider()
        result = answer_question(
            kb, llm, query="How is deadlock prevented?", user_id="alice"
        )
        assert result.has_context
        assert len(result.sources) >= 2
        prompt = llm.last_prompt.lower()
        assert "breaks the circular wait" in prompt
        assert "avoidance is used instead" in prompt
        kb.close()


class TestMissingInformationProtection:
    """Unsupported parts are admitted, not silently filled from memory."""

    def test_missing_part_rule_in_general_prompt(self) -> None:
        lower = SYSTEM_PROMPT.lower()
        assert "answer the supported part" in lower
        assert "does not contain the information for the missing part" in lower
        assert "never invent a source" in lower

    def test_missing_part_rule_in_every_intent_prompt(self) -> None:
        for system_prompt in INTENT_SYSTEM_PROMPTS.values():
            lower = system_prompt.lower()
            assert "does not contain the information for the missing part" in lower
            assert "never invent a source" in lower

    def test_comparison_intent_explicitly_names_unsupported_side(self) -> None:
        lower = INTENT_SYSTEM_PROMPTS[INTENT_COMPARISON].lower()
        assert "not provide enough information for that side" in lower

    def test_partial_material_still_produces_grounded_prompt(self) -> None:
        r1 = _make_result("TCP is connection-oriented.", material_id="m1")
        system, user = build_grounded_prompt("Explain TCP.", [r1])
        assert "TCP is connection-oriented." in user
        assert "does not contain the information for the missing part" in system.lower()


class TestSynthesisAndAttributionGuidance:
    """Synthesis + citation rules exist in every prompt flavour."""

    def test_general_prompt_tells_model_to_cite_together(self) -> None:
        lower = SYSTEM_PROMPT.lower()
        assert "synthesize" in lower
        assert "cite all the sources that support each claim together" in lower

    def test_every_intent_prompt_has_synthesis_rule(self) -> None:
        for system_prompt in INTENT_SYSTEM_PROMPTS.values():
            lower = system_prompt.lower()
            assert "synthesize: when several retrieved sources together support" in lower
            assert "cite all the sources that support each claim together" in lower

    def test_general_prompt_never_invents_sources(self) -> None:
        assert "never invent a source" in SYSTEM_PROMPT.lower()

    def test_intents_still_ground_strongly(self) -> None:
        # the Phase 1/2 grounding contract stays intact for every intent
        for system_prompt in INTENT_SYSTEM_PROMPTS.values():
            lower = system_prompt.lower()
            assert "only source of truth" in lower
            assert "outside knowledge" in lower
            assert "preserve the meaning" in lower


class TestMultiSourceConversationIntegration:
    """Follow-up turns combine sources and never reuse the previous answer."""

    def test_followup_combines_sources_and_lists_all_numbers(self, tmp_path) -> None:
        (tmp_path / "a.txt").write_text(
            "TCP is a connection-oriented transport protocol that guarantees delivery.",
            encoding="utf-8",
        )
        (tmp_path / "b.txt").write_text(
            "UDP is a connectionless protocol that favours speed over reliability.",
            encoding="utf-8",
        )
        kb = KnowledgeBase(
            DeterministicEmbedder(dimension=64),
            SqliteVectorStore(str(tmp_path / "kb.db")),
        )
        kb.index_material(
            tmp_path / "a.txt",
            source_ref=SourceRef(
                material_id="m-tcp",
                course_id="c-net",
                original_filename="a.txt",
                material_title="TCP Notes",
            ),
            uploaded_by="u1",
        )
        kb.index_material(
            tmp_path / "b.txt",
            source_ref=SourceRef(
                material_id="m-udp",
                course_id="c-net",
                original_filename="b.txt",
                material_title="UDP Notes",
            ),
            uploaded_by="u1",
        )
        llm = MockProvider()
        first = answer_question(kb, llm, query="Explain TCP.", user_id="u1")
        history = [
            ConversationTurn(
                user_message="Explain TCP.",
                resolved_query=first.resolved_query or "Explain TCP.",
                assistant_answer=first.answer,
            )
        ]
        second = answer_question(
            kb, llm, query="compare it with UDP", user_id="u1", history=history
        )
        assert second.has_context
        assert len(second.sources) >= 2
        assert [s.source_index for s in second.sources] == [1, 2]
        prompt = llm.last_prompt
        assert "SOURCE A:" in prompt
        assert "SOURCE B:" in prompt
        assert "tcp is a connection-oriented" in prompt.lower()
        assert "udp is a connectionless" in prompt.lower()
        assert "[Source 1]" in prompt and "[Source 2]" in prompt
        assert first.answer.lower() not in prompt.lower()
        kb.close()


class TestUserIsolationInSourceReasoning:
    """Evidence stays scoped: another user's material is never a source."""

    def test_other_users_material_hidden_from_sources(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_notes(kb, tmp_path, user="alice")
        evidence = collect_evidence(kb, query="deadlock prevention", user_id="bob")
        assert evidence == []
        system, user = build_grounded_prompt("deadlock prevention", [])
        assert system == NO_CONTEXT_SYSTEM_PROMPT
        assert "[Source" not in user