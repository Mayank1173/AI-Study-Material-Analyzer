"""Unit tests for Phase 3 conversation resolution (rag/conversation.py)."""

from __future__ import annotations

from rag.answer import answer_question
from rag.conversation import ConversationStore, ConversationTurn, resolve_query
from rag.intent import INTENT_COMPARISON, INTENT_EXAM, analyze_query
from rag.knowledge_base import get_knowledge_base
from rag.llm.mock_provider import MockProvider
from rag.models import SourceRef


def _turn(
    user_message: str, resolved: str | None = None, answer: str = "Assistant mock answer."
) -> ConversationTurn:
    return ConversationTurn(
        user_message=user_message,
        resolved_query=resolved or user_message,
        assistant_answer=answer,
    )


def _build_kb(tmp_path, text: str, uploaded_by: str = "u1"):
    path = tmp_path / "notes.txt"
    path.write_text(text, encoding="utf-8")
    kb = get_knowledge_base(
        store_path=str(tmp_path / "kb.db"), embedding_backend="deterministic"
    )
    kb.index_material(
        path,
        source_ref=SourceRef(
            material_id="m1",
            course_id="c1",
            original_filename="notes.txt",
            material_title="Network Notes",
        ),
        uploaded_by=uploaded_by,
    )
    return kb


class _CountingKB:
    def __init__(self, kb):
        self._kb = kb
        self.search_calls = 0

    def search(self, *args, **kwargs):
        self.search_calls += 1
        return self._kb.search(*args, **kwargs)


class TestResolution:
    def test_no_history_returns_original(self):
        r = resolve_query("What is a mutex?", [])
        assert not r.was_resolved
        assert r.resolved_query == "What is a mutex?"
        assert r.confidence == 0.0

    def test_standalone_query_not_rewritten_even_with_history(self):
        r = resolve_query("What is UDP?", [_turn("Explain TCP.")])
        assert not r.was_resolved
        assert r.resolved_query == "What is UDP?"

    def test_self_contained_pronoun_question_untouched(self):
        r = resolve_query(
            "describe photosynthesis and its role in plants",
            [_turn("Explain TCP.")],
        )
        assert not r.was_resolved
        assert r.resolved_query == "describe photosynthesis and its role in plants"

    def test_greeting_gives_no_topic_so_reference_left_unresolved(self):
        r = resolve_query("explain it", [_turn("Hello there.")])
        assert not r.was_resolved
        assert r.resolved_query == "explain it"

    def test_pronoun_resolves_to_previous_topic(self):
        r = resolve_query("what are its four conditions?", [_turn("Explain TCP.")])
        assert r.was_resolved
        assert r.resolved_query == "what are TCP's four conditions?"

    def test_pronoun_does_not_break_contraction(self):
        r = resolve_query("what about it's role?", [_turn("Explain TCP.")])
        assert r.was_resolved
        assert r.resolved_query == "what about TCP's role?"

    def test_comparison_followup_resolves(self):
        r = resolve_query("compare it with UDP", [_turn("Explain TCP.")])
        assert r.was_resolved
        assert r.resolved_query == "compare TCP with UDP"
        assert r.matched_rule == "comparison"

    def test_typo_comparison_resolves_then_phase1_corrects(self):
        r = resolve_query("comapre it with udp", [_turn("Explain TCP.")])
        assert r.was_resolved
        assert r.resolved_query == "comapre TCP with udp"
        intent = analyze_query(r.resolved_query)
        assert intent.intent_type == INTENT_COMPARISON
        assert intent.corrected_query == "compare TCP with udp"

    def test_ordinal_second_of_two_items(self):
        r = resolve_query("explain the second one", [_turn("Explain TCP and UDP.")])
        assert r.was_resolved
        assert r.resolved_query == "explain UDP"
        assert r.matched_rule == "ordinal"

    def test_ordinal_second_of_own_items(self):
        r = resolve_query("explain the second one", [_turn("Explain deadlock and its four conditions.")])
        assert r.was_resolved
        assert r.resolved_query == "explain deadlock's four conditions"

    def test_exam_mark_followup_preserves_topic(self):
        r = resolve_query("make that a 10 mark answer", [_turn("Explain deadlock.")])
        assert r.was_resolved
        assert r.resolved_query == "make deadlock a 10 mark answer"
        intent = analyze_query(r.resolved_query)
        assert intent.intent_type == INTENT_EXAM
        assert intent.requested_format == "10-mark answer"

    def test_five_mark_followup(self):
        r = resolve_query("could you make that a 5 mark answer?", [_turn("Explain deadlock.")])
        assert r.was_resolved
        assert r.resolved_query == "could you make deadlock a 5 mark answer?"
        assert analyze_query(r.resolved_query).requested_format == "5-mark answer"

    def test_low_confidence_no_topic_invention(self):
        r = resolve_query("ok go ahead", [_turn("Explain TCP.")])
        assert not r.was_resolved
        assert r.resolved_query == "ok go ahead"


class TestStore:
    def test_ensure_creates_and_get_returns_same(self):
        store = ConversationStore()
        store.ensure("c1", user_id="alice")
        assert store.get("c1", user_id="alice") is not None

    def test_ownership_is_enforced(self):
        store = ConversationStore()
        store.ensure("c1", user_id="alice")
        assert store.get("c1", user_id="bob") is None

    def test_foreign_reuse_gives_fresh_empty_conversation(self):
        store = ConversationStore()
        store.record_turn(
            "c1",
            user_id="alice",
            user_message="hi",
            resolved_query="hi",
            assistant_answer="hello",
        )
        bob = store.ensure("c1", user_id="bob")
        assert bob.history() == []
        assert bob.user_id == "bob"

    def test_record_appends_and_history_is_ordered(self):
        store = ConversationStore()
        store.ensure("c1", user_id="alice")
        store.record_turn(
            "c1", user_id="alice", user_message="q1", resolved_query="q1", assistant_answer="a1"
        )
        store.record_turn(
            "c1", user_id="alice", user_message="q2", resolved_query="q2", assistant_answer="a2"
        )
        history = store.get("c1", user_id="alice").history()
        assert [t.user_message for t in history] == ["q1", "q2"]

    def test_history_is_bounded(self):
        store = ConversationStore(max_turns=3)
        store.ensure("c1", user_id="alice")
        for i in range(5):
            store.record_turn(
                "c1",
                user_id="alice",
                user_message=f"q{i}",
                resolved_query=f"q{i}",
                assistant_answer=f"a{i}",
            )
        history = store.get("c1", user_id="alice").history()
        assert len(history) == 3
        assert [t.user_message for t in history] == ["q2", "q3", "q4"]

    def test_owner_cannot_be_reassigned(self):
        store = ConversationStore()
        store.ensure("c1", user_id="alice")
        second = store.ensure("c1", user_id="alice")
        assert second.user_id == "alice"


class TestPipeline:
    def test_followup_uses_resolved_query_for_rag(self, tmp_path):
        kb = _build_kb(
            tmp_path,
            "TCP is a connection-oriented transport protocol. "
            "UDP is connectionless and fast.",
        )
        llm = MockProvider()
        first = answer_question(kb, llm, query="Explain TCP.", user_id="u1")
        assert first.has_context
        history = [_turn("Explain TCP.", first.resolved_query or "Explain TCP.", first.answer)]
        second = answer_question(
            kb, llm, query="compare it with UDP", user_id="u1", history=history
        )
        assert second.has_context
        assert second.resolved_query == "compare TCP with UDP"
        prompt = llm.last_prompt.lower()
        assert "tcp" in prompt and "udp" in prompt

    def test_previous_answer_is_never_rag_evidence(self, tmp_path):
        kb = _build_kb(
            tmp_path,
            "TCP is a connection-oriented transport protocol. "
            "UDP is connectionless and fast.",
        )
        llm = MockProvider()
        first = answer_question(kb, llm, query="Explain TCP.", user_id="u1")
        history = [_turn("Explain TCP.", first.resolved_query or "Explain TCP.", first.answer)]
        second = answer_question(
            kb, llm, query="compare it with UDP", user_id="u1", history=history
        )
        assert first.answer.lower() not in (llm.last_prompt or "").lower()
        assert first.answer.lower() not in (llm.last_system_prompt or "").lower()

    def test_every_turn_retrieves_freshly(self, tmp_path):
        kb = _build_kb(tmp_path, "TCP is a connection-oriented protocol.")
        counting = _CountingKB(kb)
        llm = MockProvider()
        first = answer_question(counting, llm, query="Explain TCP.", user_id="u1")
        assert counting.search_calls == 1
        history = [_turn("Explain TCP.", first.resolved_query or "Explain TCP.", first.answer)]
        answer_question(
            counting, llm, query="make that a 10 mark answer", user_id="u1", history=history
        )
        assert counting.search_calls == 2
        assert llm.call_count == 2

    def test_multisource_retrieval_still_works_in_followup(self, tmp_path):
        (tmp_path / "a.txt").write_text(
            "TCP is a connection-oriented transport protocol that guarantees delivery.",
            encoding="utf-8",
        )
        (tmp_path / "b.txt").write_text(
            "UDP is a connectionless protocol that favours speed over reliability.",
            encoding="utf-8",
        )
        kb = get_knowledge_base(
            store_path=str(tmp_path / "kb.db"), embedding_backend="deterministic"
        )
        kb.index_material(
            tmp_path / "a.txt",
            source_ref=SourceRef(
                material_id="m1",
                course_id="c1",
                original_filename="a.txt",
                material_title="TCP Notes",
            ),
            uploaded_by="u1",
        )
        kb.index_material(
            tmp_path / "b.txt",
            source_ref=SourceRef(
                material_id="m2",
                course_id="c2",
                original_filename="b.txt",
                material_title="UDP Notes",
            ),
            uploaded_by="u1",
        )
        llm = MockProvider()
        first = answer_question(kb, llm, query="Explain TCP.", user_id="u1")
        history = [_turn("Explain TCP.", first.resolved_query or "Explain TCP.", first.answer)]
        second = answer_question(
            kb, llm, query="compare it with UDP", user_id="u1", history=history
        )
        assert len(second.sources) >= 2
        prompt = llm.last_prompt.lower()
        assert "tcp is a connection-oriented" in prompt
        assert "udp is a connectionless" in prompt

    def test_intent_drives_system_prompt_in_followup(self, tmp_path):
        kb = _build_kb(tmp_path, "TCP is a connection-oriented protocol. UDP is fast.")
        llm = MockProvider()
        first = answer_question(kb, llm, query="Explain TCP.", user_id="u1")
        history = [_turn("Explain TCP.", first.resolved_query or "Explain TCP.", first.answer)]
        answer_question(kb, llm, query="compare it with UDP", user_id="u1", history=history)
        assert "compare" in (llm.last_system_prompt or "").lower()

    def test_no_context_stays_no_context_in_followup(self, tmp_path):
        kb = get_knowledge_base(
            store_path=str(tmp_path / "kb.db"), embedding_backend="deterministic"
        )
        llm = MockProvider()
        first = answer_question(kb, llm, query="Explain TCP.", user_id="u1")
        assert not first.has_context
        history = [_turn("Explain TCP.", first.resolved_query or "Explain TCP.", first.answer)]
        second = answer_question(kb, llm, query="what is it?", user_id="u1", history=history)
        assert not second.has_context
        assert second.resolved_query == "what is TCP?"

    def test_llm_failure_fallback_preserves_resolution(self, tmp_path):
        class _Boom(MockProvider):
            def generate(self, *args, **kwargs):
                raise RuntimeError("boom")

        kb = _build_kb(tmp_path, "TCP is a connection-oriented protocol.")
        history = [
            ConversationTurn(
                user_message="Explain TCP.",
                resolved_query="Explain TCP.",
                assistant_answer="a",
            )
        ]
        result = answer_question(kb, _Boom(), query="what is it?", user_id="u1", history=history)
        assert result.has_context
        assert "temporarily unavailable" in result.answer
        assert result.resolved_query == "what is TCP?"