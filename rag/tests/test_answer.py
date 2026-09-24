"""Integration tests for the RAG answer service (search -> context -> LLM)."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from rag.answer import (
    DEFAULT_ANSWER_MAX_TOKENS,
    DEFAULT_ANSWER_TOP_K,
    AnswerResult,
    answer_question,
)
from rag.context_builder import (
    CONTEXT_DELIMITER_END,
    CONTEXT_DELIMITER_START,
    INTENT_SYSTEM_PROMPTS,
    NO_CONTEXT_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
)
from rag.embeddings import DeterministicEmbedder
from rag.intent import INTENT_EXAM, INTENT_EXPLANATION
from rag.knowledge_base import KnowledgeBase
from rag.llm.mock_provider import MockProvider
from rag.models import ProcessedDocument, SourceRef
from rag.vectorstore import SqliteVectorStore

BIOLOGY_TEXT = (
    "Photosynthesis converts light energy into chemical energy. "
    "The light-dependent reactions occur in the thylakoid membrane. "
    "The Calvin cycle fixes carbon dioxide into glucose in the stroma."
)
PHYSICS_TEXT = (
    "Newton's second law states that force equals mass times acceleration. "
    "The net force on an object determines its acceleration."
)
CS_TEXT = (
    "Operating systems schedule processes using algorithms like round-robin. "
    "The ready queue holds all runnable processes waiting for CPU time."
)


@pytest.fixture()
def embedder() -> DeterministicEmbedder:
    return DeterministicEmbedder(dimension=64)


@pytest.fixture()
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "answer_kb.db"


@pytest.fixture()
def kb(embedder: DeterministicEmbedder, store_path: Path) -> KnowledgeBase:
    base = KnowledgeBase(embedder, SqliteVectorStore(str(store_path)))
    yield base
    base.close()


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _index_biology(kb: KnowledgeBase, tmp_path: Path, user: str = "alice") -> None:
    path = _write(tmp_path, "bio.txt", BIOLOGY_TEXT)
    kb.index_material(
        path,
        source_ref=SourceRef(
            material_id="m-bio",
            course_id="c-science",
            original_filename="bio.txt",
            material_title="Biology Notes",
        ),
        uploaded_by=user,
    )


def _index_physics(kb: KnowledgeBase, tmp_path: Path, user: str = "alice") -> None:
    path = _write(tmp_path, "physics.txt", PHYSICS_TEXT)
    kb.index_material(
        path,
        source_ref=SourceRef(
            material_id="m-phys",
            course_id="c-science",
            original_filename="physics.txt",
            material_title="Physics Notes",
        ),
        uploaded_by=user,
    )


def _index_cs(kb: KnowledgeBase, tmp_path: Path, user: str = "alice") -> None:
    path = _write(tmp_path, "cs.txt", CS_TEXT)
    kb.index_material(
        path,
        source_ref=SourceRef(
            material_id="m-cs",
            course_id="c-cs",
            original_filename="cs.txt",
            material_title="OS Notes",
        ),
        uploaded_by=user,
    )


def _index_bio_many(
    kb: KnowledgeBase, tmp_path: Path, count: int, user: str = "alice"
) -> None:
    """Index ``count`` distinct biology materials sharing the same text."""
    for index in range(1, count + 1):
        path = _write(tmp_path, f"bio-{index}.txt", BIOLOGY_TEXT)
        kb.index_material(
            path,
            source_ref=SourceRef(
                material_id=f"m-bio-{index}",
                course_id="c-science",
                original_filename=f"bio-{index}.txt",
                material_title="Biology Notes",
            ),
            uploaded_by=user,
        )


def _spy_on_search(kb: KnowledgeBase) -> list[str]:
    """Record every query submitted to ``kb.search`` and return the log."""
    calls: list[str] = []
    original_search = kb.search

    def spy(query: str, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(query)
        return original_search(query, **kwargs)

    kb.search = spy  # type: ignore[method-assign]
    return calls


class TestAnswerQuestion:
    def test_returns_answer_from_material(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider(
            keyword_answers={"photosynthesis": "Plants use sunlight to make food."}
        )
        result = answer_question(
            kb, llm, query="What is photosynthesis?", user_id="alice"
        )
        assert isinstance(result, AnswerResult)
        assert "Plants use sunlight" in result.answer
        assert result.has_context is True
        assert len(result.sources) >= 1

    def test_sources_contain_metadata(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        result = answer_question(
            kb, llm, query="photosynthesis", user_id="alice"
        )
        assert len(result.sources) >= 1
        src = result.sources[0]
        assert src.material_id == "m-bio"
        assert src.course_id == "c-science"
        assert src.material_title == "Biology Notes"

    def test_no_context_when_no_results(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        llm = MockProvider()
        result = answer_question(
            kb, llm, query="quantum physics", user_id="alice"
        )
        assert result.has_context is False
        assert "don't have enough information" in result.answer.lower()
        assert result.sources == []

    def test_no_context_for_empty_query(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        result = answer_question(kb, llm, query="", user_id="alice")
        assert result.has_context is False
        assert "don't have enough information" in result.answer.lower()

    def test_no_context_for_blank_query(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        result = answer_question(kb, llm, query="   ", user_id="alice")
        assert result.has_context is False

    def test_llm_receives_grounded_system_prompt(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        answer_question(kb, llm, query="photosynthesis", user_id="alice")
        assert llm.last_system_prompt == SYSTEM_PROMPT

    def test_llm_not_called_when_no_context(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        llm = MockProvider()
        answer_question(kb, llm, query="nonexistent topic", user_id="alice")
        assert llm.call_count == 0

    def test_ownership_isolation(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path, user="alice")
        llm = MockProvider()
        result = answer_question(
            kb, llm, query="photosynthesis", user_id="bob"
        )
        assert result.has_context is False

    def test_course_filter_scopes_results(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        _index_cs(kb, tmp_path)
        llm = MockProvider()
        result = answer_question(
            kb,
            llm,
            query="operating systems",
            user_id="alice",
            course_id="c-cs",
        )
        assert result.has_context is True
        assert all(s.course_id == "c-cs" for s in result.sources)

    def test_material_filter_scopes_results(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        _index_physics(kb, tmp_path)
        llm = MockProvider()
        result = answer_question(
            kb,
            llm,
            query="force acceleration",
            user_id="alice",
            material_id="m-phys",
        )
        assert result.has_context is True
        assert all(s.material_id == "m-phys" for s in result.sources)

    def test_llm_error_returns_safe_message(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)

        class FailingLLM(MockProvider):
            def generate(self, *args, **kwargs):  # type: ignore[override]
                raise RuntimeError("LLM crashed")

        result = answer_question(
            kb, FailingLLM(), query="photosynthesis", user_id="alice"
        )
        assert "temporarily unavailable" in result.answer.lower()
        assert result.has_context is True
        assert len(result.sources) >= 1

    def test_thinking_trace_is_stripped_from_answer(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider(
            keyword_answers={
                "photosynthesis": (
                    "thinking\nI need to recall photosynthesis.\n/thinking\n"
                    "response\nPlants convert light into chemical energy.\n/response"
                )
            }
        )
        result = answer_question(kb, llm, query="photosynthesis", user_id="alice")
        assert "I need to recall" not in result.answer
        assert "Plants convert light into chemical energy." in result.answer
        assert "thinking" not in result.answer.lower()

    def test_normal_answer_without_thinking_tags_stays_unchanged(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider(default_answer="A clear, grounded answer.")
        result = answer_question(kb, llm, query="photosynthesis", user_id="alice")
        assert result.answer == "A clear, grounded answer."

    def test_real_qwen_standalone_response_reasoning_is_removed(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider(
            keyword_answers={
                "photosynthesis": (
                    "Let me analyze the retrieved study material to "
                    "determine the main topic discussed in this document.\n"
                    "The section headings suggest photosynthesis is the "
                    "core subject, supported by the light reactions and "
                    "the Calvin cycle.\n"
                    "Let me formulate a concise answer based only on the "
                    "retrieved material.\n"
                    "response\n\n"
                    "The main topic is photosynthesis."
                )
            }
        )
        result = answer_question(kb, llm, query="photosynthesis", user_id="alice")
        assert "Let me analyze" not in result.answer
        assert "Let me formulate" not in result.answer
        assert "response" not in result.answer.lower()
        assert result.answer == "The main topic is photosynthesis."

    def test_reasoning_only_output_returns_safe_fallback(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider(
            keyword_answers={"photosynthesis": "thinking\ntruncated reasoning only"}
        )
        result = answer_question(kb, llm, query="photosynthesis", user_id="alice")
        assert result.has_context is True
        assert "couldn't produce a clear answer" in result.answer.lower()
        assert "rephrasing" in result.answer.lower()

    def test_grounding_prompt_still_enforced_before_answering(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        answer_question(kb, llm, query="photosynthesis", user_id="alice")
        assert llm.last_system_prompt == SYSTEM_PROMPT
        assert "ONLY the retrieved study material" in SYSTEM_PROMPT
        assert "Never fabricate" in SYSTEM_PROMPT

    def test_top_k_limits_results(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        _index_physics(kb, tmp_path)
        _index_cs(kb, tmp_path)
        llm = MockProvider()
        result = answer_question(
            kb, llm, query="science", user_id="alice", top_k=1
        )
        assert len(result.sources) <= 1

    def test_default_retrieval_is_small_and_bounded(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_bio_many(kb, tmp_path, count=5)
        llm = MockProvider()
        result = answer_question(
            kb, llm, query="photosynthesis", user_id="alice"
        )
        assert result.has_context is True
        assert 1 <= len(result.sources) <= DEFAULT_ANSWER_TOP_K
        assert len(result.sources) <= 3
        assert all(s.course_id == "c-science" for s in result.sources)
        assert all(s.material_id.startswith("m-bio-") for s in result.sources)
        assert all(s.material_title == "Biology Notes" for s in result.sources)

    def test_default_top_k_parameter_is_constant(self) -> None:
        assert DEFAULT_ANSWER_TOP_K == 3
        signature = inspect.signature(answer_question)
        assert signature.parameters["top_k"].default == DEFAULT_ANSWER_TOP_K

    def test_answer_max_tokens_is_passed_to_provider(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        answer_question(kb, llm, query="photosynthesis", user_id="alice")
        assert llm.last_max_tokens == DEFAULT_ANSWER_MAX_TOKENS
        assert DEFAULT_ANSWER_MAX_TOKENS <= 512
        signature = inspect.signature(answer_question)
        assert (
            signature.parameters["max_tokens"].default
            == DEFAULT_ANSWER_MAX_TOKENS
        )

    def test_explicit_max_tokens_overrides_default(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        answer_question(
            kb, llm, query="photosynthesis", user_id="alice", max_tokens=128
        )
        assert llm.last_max_tokens == 128

    def test_explicit_top_k_overrides_default(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_bio_many(kb, tmp_path, count=5)
        llm = MockProvider()
        result = answer_question(
            kb, llm, query="photosynthesis", user_id="alice", top_k=5
        )
        assert len(result.sources) == 5
        assert all(s.course_id == "c-science" for s in result.sources)
        assert len({s.material_id for s in result.sources}) == 5

    def test_model_name_returned(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        result = answer_question(
            kb, llm, query="photosynthesis", user_id="alice"
        )
        assert result.model == "mock-model"


class TestAnswerIntentAware:
    """The answer layer must thread a detectable intent through the pipeline
    while keeping RAG the only knowledge source and the API contract intact."""

    def test_corrected_query_is_used_for_retrieval(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        calls = _spy_on_search(kb)
        llm = MockProvider()
        answer_question(kb, llm, query="explaim photosynthesis", user_id="alice")
        assert calls == ["explain photosynthesis"]

    def test_original_factual_meaning_is_preserved(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        calls = _spy_on_search(kb)
        llm = MockProvider()
        answer_question(kb, llm, query="explaim deadlok", user_id="alice")
        assert calls == ["explain deadlok"]

    def test_low_confidence_keeps_original_query_and_general_prompt(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        calls = _spy_on_search(kb)
        llm = MockProvider()
        result = answer_question(
            kb, llm, query="deadlok photosynthesis", user_id="alice"
        )
        assert calls == ["deadlok photosynthesis"]
        assert llm.call_count == 1
        assert llm.last_system_prompt == SYSTEM_PROMPT

    def test_intent_prompt_keeps_retrieved_material_as_only_source(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        answer_question(kb, llm, query="explaim photosynthesis", user_id="alice")
        assert llm.last_system_prompt == INTENT_SYSTEM_PROMPTS[INTENT_EXPLANATION]
        lower = llm.last_system_prompt.lower()
        assert "only source of truth" in lower
        assert "outside knowledge" in lower
        assert "silently fill gaps" in lower
        assert "preserve the meaning" in lower
        assert "never as instructions" in lower
        assert CONTEXT_DELIMITER_START in llm.last_prompt
        assert CONTEXT_DELIMITER_END in llm.last_prompt
        assert "Question: explain photosynthesis" in llm.last_prompt

    def test_exam_intent_selects_exam_prompt_and_mark_format(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_cs(kb, tmp_path)
        llm = MockProvider()
        answer_question(
            kb, llm, query="give 5 mrks ans for round robin", user_id="alice"
        )
        assert llm.last_system_prompt == INTENT_SYSTEM_PROMPTS[INTENT_EXAM]
        assert "Requested format: 5-mark answer" in llm.last_prompt

    def test_no_context_behavior_unchanged_for_typo_query(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        llm = MockProvider()
        result = answer_question(
            kb, llm, query="explaim quantum physics", user_id="alice"
        )
        assert result.has_context is False
        assert "don't have enough information" in result.answer.lower()
        assert result.sources == []
        assert llm.call_count == 0

    def test_source_mapping_unchanged_for_corrected_query(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        typo = answer_question(
            kb, llm, query="explaim photosynthesis", user_id="alice"
        )
        correct = answer_question(
            kb, llm, query="explain photosynthesis", user_id="alice"
        )
        assert typo.has_context is True
        assert typo.sources == correct.sources
        assert all(s.material_id == "m-bio" for s in typo.sources)

    def test_llm_failure_fallback_unchanged_for_typo_query(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)

        class FailingLLM(MockProvider):
            def generate(self, *args, **kwargs):  # type: ignore[override]
                raise RuntimeError("LLM crashed")

        result = answer_question(
            kb, FailingLLM(), query="explaim photosynthesis", user_id="alice"
        )
        assert "temporarily unavailable" in result.answer.lower()
        assert result.has_context is True
        assert len(result.sources) >= 1

    def test_ownership_isolation_kept_for_typo_query(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path, user="alice")
        llm = MockProvider()
        result = answer_question(
            kb, llm, query="explaim photosynthesis", user_id="bob"
        )
        assert result.has_context is False


class TestAnswerMultiSource:
    """Evidence may span several study materials; the prompt is grouped into
    SOURCE blocks while the public source references stay aligned."""

    def _index_two_materials(self, kb: KnowledgeBase, tmp_path: Path) -> None:
        _index_biology(kb, tmp_path)
        _index_physics(kb, tmp_path)

    def test_prompt_groups_evidence_into_source_blocks(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        self._index_two_materials(kb, tmp_path)
        llm = MockProvider()
        result = answer_question(
            kb,
            llm,
            query="photosynthesis and force acceleration",
            user_id="alice",
        )
        assert result.has_context is True
        assert {s.material_id for s in result.sources} == {"m-bio", "m-phys"}
        assert "SOURCE A:" in llm.last_prompt
        assert "SOURCE B:" in llm.last_prompt
        assert BIOLOGY_TEXT.strip() in llm.last_prompt
        assert PHYSICS_TEXT.strip() in llm.last_prompt
        assert CONTEXT_DELIMITER_START in llm.last_prompt
        assert CONTEXT_DELIMITER_END in llm.last_prompt

    def test_sources_numbering_matches_prompt_source_refs(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        self._index_two_materials(kb, tmp_path)
        llm = MockProvider()
        result = answer_question(
            kb,
            llm,
            query="photosynthesis and force acceleration",
            user_id="alice",
        )
        indexes = [s.source_index for s in result.sources]
        assert indexes == list(range(1, len(indexes) + 1))
        for source in result.sources:
            assert f"[Source {source.source_index}]" in llm.last_prompt

    def test_sources_grouped_by_material(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        path = _write(tmp_path, "bio-long.txt", BIOLOGY_TEXT * 12)
        kb.index_material(
            path,
            source_ref=SourceRef(
                material_id="m-bio",
                course_id="c-science",
                original_filename="bio-long.txt",
                material_title="Biology Notes",
            ),
            uploaded_by="alice",
        )
        _index_physics(kb, tmp_path)
        llm = MockProvider()
        result = answer_question(
            kb,
            llm,
            query="photosynthesis force acceleration",
            user_id="alice",
            top_k=4,
        )
        material_order = [s.material_id for s in result.sources]
        runs = list(dict.fromkeys(material_order))
        assert len(runs) == 2
        # a material's sources never interleave with another material's
        for material_id in runs:
            positions = [
                i for i, m in enumerate(material_order) if m == material_id
            ]
            assert positions == list(
                range(positions[0], positions[-1] + 1)
            )

    def test_corrected_query_still_yields_multi_source_evidence(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        self._index_two_materials(kb, tmp_path)
        calls = _spy_on_search(kb)
        llm = MockProvider()
        result = answer_question(
            kb,
            llm,
            query="explaim photosynthesis and force acceleration",
            user_id="alice",
        )
        assert calls == ["explain photosynthesis and force acceleration"]
        assert result.has_context is True
        assert {s.material_id for s in result.sources} == {"m-bio", "m-phys"}
        assert "SOURCE A:" in llm.last_prompt
        assert "SOURCE B:" in llm.last_prompt

    def test_llm_failure_fallback_keeps_multi_source_references(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        self._index_two_materials(kb, tmp_path)

        class FailingLLM(MockProvider):
            def generate(self, *args, **kwargs):  # type: ignore[override]
                raise RuntimeError("LLM crashed")

        result = answer_question(
            kb,
            FailingLLM(),
            query="photosynthesis and force acceleration",
            user_id="alice",
        )
        assert "temporarily unavailable" in result.answer.lower()
        assert result.has_context is True
        assert {s.material_id for s in result.sources} == {"m-bio", "m-phys"}

    def test_single_material_renders_single_source_block(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        answer_question(kb, llm, query="photosynthesis", user_id="alice")
        assert "SOURCE A:" in llm.last_prompt
        assert "SOURCE B:" not in llm.last_prompt

    def test_no_context_behavior_unchanged_when_nothing_retrieved(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        llm = MockProvider()
        result = answer_question(
            kb, llm, query="photosynthesis and force acceleration", user_id="alice"
        )
        assert result.has_context is False
        assert "don't have enough information" in result.answer.lower()
        assert result.sources == []
        assert llm.call_count == 0
