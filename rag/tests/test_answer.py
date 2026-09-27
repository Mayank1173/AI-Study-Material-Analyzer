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
    NO_CONTEXT_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    ConversationTurn,
)
from rag.embeddings import DeterministicEmbedder
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

    def test_answers_general_question_without_matching_material(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        """A question unrelated to the index is still answered normally."""
        _index_biology(kb, tmp_path)
        llm = MockProvider(
            keyword_answers={"japan": "The capital of Japan is Tokyo."}
        )
        result = answer_question(
            kb, llm, query="What is the capital of Japan?", user_id="alice"
        )
        assert "Tokyo" in result.answer
        assert "don't have enough information" not in result.answer.lower()
        assert llm.call_count == 1

    def test_answers_general_question_with_no_material_at_all(
        self, kb: KnowledgeBase
    ) -> None:
        llm = MockProvider(
            keyword_answers={"photosynthesis": "Plants use light to make food."}
        )
        result = answer_question(
            kb, llm, query="What is photosynthesis?", user_id="alice"
        )
        assert "Plants use light" in result.answer
        assert result.has_context is False
        assert result.sources == []
        assert llm.call_count == 1
        assert llm.last_system_prompt == NO_CONTEXT_SYSTEM_PROMPT

    def test_has_no_context_when_no_results(self, kb: KnowledgeBase) -> None:
        """No material is retrieved, but the question is still answered."""
        llm = MockProvider(default_answer="Entropy is a measure of disorder.")
        result = answer_question(kb, llm, query="entropy", user_id="alice")
        assert result.has_context is False
        assert "measure of disorder" in result.answer
        assert "don't have enough information" not in result.answer.lower()
        assert result.sources == []

    def test_empty_query_asks_for_a_question(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        result = answer_question(kb, llm, query="", user_id="alice")
        assert result.has_context is False
        assert "type a question" in result.answer.lower()
        assert result.sources == []
        assert llm.call_count == 0

    def test_blank_query_asks_for_a_question(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        result = answer_question(kb, llm, query="   ", user_id="alice")
        assert result.has_context is False
        assert "type a question" in result.answer.lower()
        assert llm.call_count == 0

    def test_llm_receives_grounded_system_prompt(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        answer_question(kb, llm, query="photosynthesis", user_id="alice")
        assert llm.last_system_prompt == SYSTEM_PROMPT

    def test_llm_is_called_even_when_no_context(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        llm = MockProvider()
        answer_question(kb, llm, query="nonexistent topic", user_id="alice")
        assert llm.call_count == 1

    def test_ownership_isolation(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path, user="alice")
        llm = MockProvider()
        result = answer_question(
            kb, llm, query="photosynthesis", user_id="bob"
        )
        assert result.has_context is False
        assert result.sources == []

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
        assert "Never fabricate" in SYSTEM_PROMPT
        assert "never the only source of knowledge" in SYSTEM_PROMPT

    def test_history_is_passed_to_the_prompt(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        answer_question(
            kb,
            llm,
            query="Give me another example.",
            user_id="alice",
            history=[
                ConversationTurn(role="user", content="What is photosynthesis?"),
                ConversationTurn(
                    role="assistant", content="Plants use light to make food."
                ),
            ],
        )
        assert "User: What is photosynthesis?" in llm.last_prompt
        assert "Assistant: Plants use light to make food." in llm.last_prompt
        assert "Question: Give me another example." in llm.last_prompt

    def test_history_is_used_to_retrieve_for_follow_ups(
        self, kb: KnowledgeBase, tmp_path: Path
    ) -> None:
        """A bare follow-up still retrieves the material it refers to."""
        _index_biology(kb, tmp_path)
        llm = MockProvider()
        result = answer_question(
            kb,
            llm,
            query="Give me another example.",
            user_id="alice",
            history=[
                ConversationTurn(role="user", content="Explain photosynthesis."),
            ],
        )
        assert result.has_context is True
        assert len(result.sources) >= 1
        assert all(s.material_id == "m-bio" for s in result.sources)

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
