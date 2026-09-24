"""Tests for Phase 3 conversation support on the /api/chat endpoint."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.chat import (
    _get_kb as chat_get_kb,
    get_conversation_store as chat_get_conversation_store,
    get_llm_provider as chat_get_llm_provider,
)
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models import Course, StudyMaterial, User
from main import app
from rag.conversation import ConversationStore
from rag.knowledge_base import get_knowledge_base
from rag.llm.mock_provider import MockProvider
from rag.models import SourceRef

TEST_PASSWORD = "testpassword123"

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def _enable_fk(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSession = sessionmaker(
    bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def _reset():
    global _course_counter
    _course_counter = 0
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)


def _make_user(name: str, email: str) -> User:
    db = TestingSession()
    user = User(
        name=name, email=email, password_hash=hash_password(TEST_PASSWORD)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


_course_counter = 0


def _make_course(db, teacher_id: uuid.UUID, name: str = "CS101") -> Course:
    global _course_counter
    _course_counter += 1
    course = Course(
        teacher_id=teacher_id,
        name=name,
        code=f"TEST{_course_counter:04d}",
        description="Test course",
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def _make_material(
    db,
    course_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str = "Lecture 1",
    status: str = "uploaded",
) -> StudyMaterial:
    mat = StudyMaterial(
        course_id=course_id,
        uploaded_by=user_id,
        title=title,
        material_type="lecture_notes",
        status=status,
    )
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat


def _make_kb(tmp_path, text: str, uploaded_by: str, material_id: str) -> "KnowledgeBase":
    path = tmp_path / "notes.txt"
    path.write_text(text, encoding="utf-8")
    kb = get_knowledge_base(
        store_path=str(tmp_path / "chat_kb.db"),
        embedding_backend="deterministic",
    )
    kb.index_material(
        path,
        source_ref=SourceRef(
            material_id=material_id,
            course_id="c-conv",
            original_filename="notes.txt",
            material_title="Network Notes",
        ),
        uploaded_by=uploaded_by,
    )
    return kb


@pytest.fixture()
def client():
    _reset()
    mock_llm = MockProvider()
    store = ConversationStore()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    def override_llm():
        return mock_llm

    def override_convo_store():
        return store

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[chat_get_llm_provider] = override_llm
    app.dependency_overrides[chat_get_conversation_store] = override_convo_store

    with TestClient(app) as c:
        yield c, mock_llm, store

    app.dependency_overrides.clear()


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


class TestConversationRequestValidation:
    def test_conversation_id_too_long_rejected(self, client) -> None:
        c, _, _ = client
        user = _make_user("Alice", "alice@example.com")
        resp = c.post(
            "/api/chat",
            json={"message": "Hello", "conversation_id": "x" * 65},
            headers=_headers(user),
        )
        assert resp.status_code == 422

    def test_response_schema_unchanged_with_conversation(self, client) -> None:
        c, _, _ = client
        user = _make_user("Alice", "alice@example.com")
        resp = c.post(
            "/api/chat",
            json={"message": "Hello", "conversation_id": "conv-1"},
            headers=_headers(user),
        )
        assert resp.status_code == 200
        assert set(resp.json().keys()) == {"answer", "sources", "has_context"}


class TestConversationRecording:
    def test_without_conversation_id_nothing_is_recorded(self, client) -> None:
        c, _, store = client
        user = _make_user("Alice", "alice@example.com")
        resp = c.post(
            "/api/chat",
            json={"message": "Explain TCP."},
            headers=_headers(user),
        )
        assert resp.status_code == 200
        assert store.get("conv-none", user_id=str(user.id)) is None

    def test_first_turn_recorded_as_standalone(self, client) -> None:
        c, mock_llm, store = client
        user = _make_user("Alice", "alice@example.com")
        resp = c.post(
            "/api/chat",
            json={"message": "Explain TCP.", "conversation_id": "conv-1"},
            headers=_headers(user),
        )
        assert resp.status_code == 200
        history = store.get("conv-1", user_id=str(user.id)).history()
        assert len(history) == 1
        assert history[0].user_message == "Explain TCP."
        assert mock_llm.last_prompt == ""  # no context, no LLM call


class TestConversationFollowUp:
    def test_followup_uses_resolved_query_and_records_turn(
        self, client, tmp_path
    ) -> None:
        c, mock_llm, store = client
        user = _make_user("Alice", "alice@example.com")
        kb = _make_kb(
            tmp_path,
            "TCP is a connection-oriented transport protocol. "
            "UDP is connectionless and fast.",
            uploaded_by=str(user.id),
            material_id="m-tcp-udp",
        )

        def override_kb():
            return kb

        app.dependency_overrides[chat_get_kb] = override_kb
        try:
            first = c.post(
                "/api/chat",
                json={"message": "Explain TCP.", "conversation_id": "conv-1"},
                headers=_headers(user),
            )
            second = c.post(
                "/api/chat",
                json={"message": "compare it with UDP", "conversation_id": "conv-1"},
                headers=_headers(user),
            )
        finally:
            app.dependency_overrides.clear()
            kb.close()

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["has_context"] is True
        assert second.json()["has_context"] is True
        prompt = mock_llm.last_prompt.lower()
        assert "compare tcp with udp" in prompt
        assert "udp" in prompt and "tcp" in prompt

        history = store.get("conv-1", user_id=str(user.id)).history()
        assert len(history) == 2
        assert history[1].resolved_query == "compare TCP with UDP"

    def test_previous_answer_never_enters_grounded_prompt(
        self, client, tmp_path
    ) -> None:
        c, mock_llm, store = client
        user = _make_user("Alice", "alice@example.com")
        kb = _make_kb(
            tmp_path,
            "TCP is a connection-oriented transport protocol. "
            "UDP is connectionless and fast.",
            uploaded_by=str(user.id),
            material_id="m-tcp-udp",
        )

        def override_kb():
            return kb

        app.dependency_overrides[chat_get_kb] = override_kb
        try:
            first = c.post(
                "/api/chat",
                json={"message": "Explain TCP.", "conversation_id": "conv-1"},
                headers=_headers(user),
            )
            second = c.post(
                "/api/chat",
                json={"message": "compare it with UDP", "conversation_id": "conv-1"},
                headers=_headers(user),
            )
        finally:
            app.dependency_overrides.clear()
            kb.close()

        assert first.json()["answer"].lower() not in (mock_llm.last_prompt or "").lower()
        assert first.json()["answer"].lower() not in (
            mock_llm.last_system_prompt or ""
        ).lower()

    def test_followup_no_context_stays_no_context_and_records(
        self, client
    ) -> None:
        c, _, store = client
        user = _make_user("Alice", "alice@example.com")
        first = c.post(
            "/api/chat",
            json={"message": "Explain TCP.", "conversation_id": "conv-2"},
            headers=_headers(user),
        )
        second = c.post(
            "/api/chat",
            json={"message": "what is it?", "conversation_id": "conv-2"},
            headers=_headers(user),
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["has_context"] is False
        assert second.json()["has_context"] is False
        history = store.get("conv-2", user_id=str(user.id)).history()
        assert len(history) == 2
        assert history[1].resolved_query == "what is TCP?"


class TestConversationScoping:
    def test_foreign_conversation_id_never_leaks_history(self, client, tmp_path) -> None:
        c, mock_llm, store = client
        alice = _make_user("Alice", "alice@example.com")
        bob = _make_user("Bob", "bob@example.com")
        headers_alice = _headers(alice)
        headers_bob = _headers(bob)

        path_a = tmp_path / "a.txt"
        path_a.write_text("TCP guarantees ordered, reliable delivery.", encoding="utf-8")
        path_b = tmp_path / "b.txt"
        path_b.write_text("UDP is a connectionless, fast protocol.", encoding="utf-8")
        kb = get_knowledge_base(
            store_path=str(tmp_path / "conv_kb.db"),
            embedding_backend="deterministic",
        )
        kb.index_material(
            path_a,
            source_ref=SourceRef(
                material_id="m-a",
                course_id="c-a",
                original_filename="a.txt",
                material_title="Network Notes",
            ),
            uploaded_by=str(alice.id),
        )
        kb.index_material(
            path_b,
            source_ref=SourceRef(
                material_id="m-b",
                course_id="c-b",
                original_filename="b.txt",
                material_title="Network Notes",
            ),
            uploaded_by=str(bob.id),
        )

        def override_kb():
            return kb

        app.dependency_overrides[chat_get_kb] = override_kb
        try:
            alice_first = c.post(
                "/api/chat",
                json={"message": "Explain TCP.", "conversation_id": "shared"},
                headers=headers_alice,
            )
            bob_first = c.post(
                "/api/chat",
                json={"message": "Explain UDP.", "conversation_id": "shared"},
                headers=headers_bob,
            )
            bob_second = c.post(
                "/api/chat",
                json={"message": "what is it?", "conversation_id": "shared"},
                headers=headers_bob,
            )
        finally:
            app.dependency_overrides.clear()
            kb.close()

        assert alice_first.status_code == 200
        assert bob_first.status_code == 200
        assert bob_second.status_code == 200
        prompt = mock_llm.last_prompt.lower()
        assert "udp" in prompt
        assert "tcp" not in prompt

        # Bob's use of "shared" replaced Alice's foreign conversation with a
        # fresh one owned by Bob; Alice's history is never readable by Bob and
        # is discarded from the in-memory store.
        assert store.get("shared", user_id=str(alice.id)) is None
        assert len(store.get("shared", user_id=str(bob.id)).history()) == 2
        assert store.get("shared", user_id=str(bob.id)).history()[0].user_message == (
            "Explain UDP."
        )

    def test_course_filter_preserved_in_followup(self, client, tmp_path) -> None:
        c, _, store = client
        user = _make_user("Alice", "alice@example.com")

        p1 = tmp_path / "a.txt"
        p1.write_text("Deadlock occurs when processes wait forever.", encoding="utf-8")
        p2 = tmp_path / "b.txt"
        p2.write_text("Caching stores frequently used data in memory.", encoding="utf-8")
        kb = get_knowledge_base(
            store_path=str(tmp_path / "filter_kb.db"),
            embedding_backend="deterministic",
        )
        kb.index_material(
            p1,
            source_ref=SourceRef(
                material_id="m-os",
                course_id="c-os",
                original_filename="a.txt",
                material_title="OS Notes",
            ),
            uploaded_by=str(user.id),
        )
        kb.index_material(
            p2,
            source_ref=SourceRef(
                material_id="m-sys",
                course_id="c-sys",
                original_filename="b.txt",
                material_title="Systems Notes",
            ),
            uploaded_by=str(user.id),
        )

        def override_kb():
            return kb

        app.dependency_overrides[chat_get_kb] = override_kb
        try:
            first = c.post(
                "/api/chat",
                json={
                    "message": "Explain deadlock.",
                    "course_id": "c-os",
                    "conversation_id": "conv-3",
                },
                headers=_headers(user),
            )
            second = c.post(
                "/api/chat",
                json={
                    "message": "what are its four conditions?",
                    "course_id": "c-os",
                    "conversation_id": "conv-3",
                },
                headers=_headers(user),
            )
        finally:
            app.dependency_overrides.clear()
            kb.close()

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["has_context"] is True
        assert all(s["course_id"] == "c-os" for s in second.json()["sources"])
        history = store.get("conv-3", user_id=str(user.id)).history()
        assert history[1].resolved_query == "what are deadlock's four conditions?"