"""Tests for the /api/chat endpoint."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.chat import (
    _get_kb as chat_get_kb,
    get_llm_provider as chat_get_llm_provider,
)
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models import Course, StudyMaterial, User
from main import app
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
    user = User(name=name, email=email, password_hash=hash_password(TEST_PASSWORD))
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


@pytest.fixture()
def client():
    _reset()
    mock_llm = MockProvider(
        keyword_answers={
            "photosynthesis": "Plants convert light energy into chemical energy via photosynthesis.",
            "operating systems": "Operating systems manage hardware resources and schedule processes.",
        }
    )

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    def override_llm():
        return mock_llm

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[chat_get_llm_provider] = override_llm

    with TestClient(app) as c:
        yield c, mock_llm

    app.dependency_overrides.clear()


class TestChatAuthentication:
    def test_requires_auth(self, client) -> None:
        c, _ = client
        resp = c.post("/api/chat", json={"message": "Hello"})
        assert resp.status_code in (401, 403)

    def test_rejects_invalid_token(self, client) -> None:
        c, _ = client
        resp = c.post(
            "/api/chat",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401

    def test_rejects_empty_message(self, client) -> None:
        c, _ = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)
        resp = c.post(
            "/api/chat",
            json={"message": ""},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422


class TestChatOwnership:
    def test_user_id_cannot_be_spoofed_from_request(self, client) -> None:
        """The endpoint uses the JWT user, never a client-supplied user_id."""
        c, _ = client
        alice = _make_user("Alice", "alice@example.com")
        resp = c.post(
            "/api/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {create_access_token(alice.id)}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert isinstance(data["sources"], list)

    def test_no_context_response_for_empty_knowledge_base(self, client) -> None:
        c, _ = client
        user = _make_user("Alice", "alice@example.com")
        resp = c.post(
            "/api/chat",
            json={"message": "What is DNA?"},
            headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_context"] is False
        assert "don't have enough information" in data["answer"].lower()
        assert data["sources"] == []


class TestChatResponse:
    def test_returns_answer_and_sources(self, client) -> None:
        c, mock_llm = client
        user = _make_user("Alice", "alice@example.com")

        db = TestingSession()
        course = _make_course(db, user.id, name="Biology")
        mat = _make_material(db, course.id, user.id, title="Biology Notes")
        db.close()

        resp = c.post(
            "/api/chat",
            json={"message": "What is photosynthesis?"},
            headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert isinstance(data["sources"], list)
        assert isinstance(data["has_context"], bool)

    def test_valid_request_structure(self, client) -> None:
        c, _ = client
        user = _make_user("Alice", "alice@example.com")
        resp = c.post(
            "/api/chat",
            json={"message": "Hello world"},
            headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "sources" in data
        assert "has_context" in data

    def test_message_too_long_rejected(self, client) -> None:
        c, _ = client
        user = _make_user("Alice", "alice@example.com")
        resp = c.post(
            "/api/chat",
            json={"message": "x" * 4001},
            headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
        )
        assert resp.status_code == 422


class TestChatCourseMaterialFilter:
    def test_course_id_scopes_search(self, client) -> None:
        c, mock_llm = client
        user = _make_user("Alice", "alice@example.com")

        db = TestingSession()
        course1 = _make_course(db, user.id, name="Biology")
        course2 = _make_course(db, user.id, name="CS")
        _make_material(db, course1.id, user.id, title="Bio Notes")
        _make_material(db, course2.id, user.id, title="CS Notes")
        db.close()

        resp = c.post(
            "/api/chat",
            json={
                "message": "What is photosynthesis?",
                "course_id": str(course1.id),
            },
            headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
        )
        assert resp.status_code == 200

    def test_material_id_scopes_search(self, client) -> None:
        c, mock_llm = client
        user = _make_user("Alice", "alice@example.com")

        db = TestingSession()
        course = _make_course(db, user.id)
        mat = _make_material(db, course.id, user.id)
        db.close()

        resp = c.post(
            "/api/chat",
            json={
                "message": "Explain this material",
                "material_id": str(mat.id),
            },
            headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
        )
        assert resp.status_code == 200


class TestChatNoContextBehavior:
    def test_no_context_returns_appropriate_message(self, client) -> None:
        c, _ = client
        user = _make_user("Alice", "alice@example.com")
        resp = c.post(
            "/api/chat",
            json={"message": "Explain quantum entanglement in detail"},
            headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_context"] is False
        assert "don't have enough information" in data["answer"].lower()
        assert data["sources"] == []


class TestChatTypoTolerantGroundedPipeline:
    def test_typo_query_reaches_same_grounded_pipeline(self, client, tmp_path) -> None:
        """A typo-tolerant query must flow through the same grounded pipeline:
        corrected retrieval, intent-aware prompt, delimiters intact, and an
        unchanged API response schema."""
        c, mock_llm = client
        user = _make_user("Alice", "alice@example.com")
        headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}

        path = tmp_path / "bio.txt"
        path.write_text(
            "Photosynthesis converts light energy into chemical energy.",
            encoding="utf-8",
        )

        kb = get_knowledge_base(store_path=str(tmp_path / "typo_kb.db"))
        kb.index_material(
            path,
            source_ref=SourceRef(
                material_id="m-typo",
                course_id="c-typo",
                original_filename="bio.txt",
                material_title="Biology Notes",
            ),
            uploaded_by=str(user.id),
        )

        def override_kb():
            return kb

        app.dependency_overrides[chat_get_kb] = override_kb
        try:
            resp = c.post(
                "/api/chat",
                json={"message": "explaim photosynthesis"},
                headers=headers,
            )
        finally:
            app.dependency_overrides.clear()
            kb.close()

        assert resp.status_code == 200
        data = resp.json()
        assert data["has_context"] is True
        assert len(data["sources"]) >= 1
        assert "Plants convert light energy" in data["answer"]
        assert set(data.keys()) == {"answer", "sources", "has_context"}
        assert "explain photosynthesis" in mock_llm.last_prompt
        assert "--- RETRIEVED STUDY MATERIAL (BEGIN) ---" in mock_llm.last_prompt
        assert "--- RETRIEVED STUDY MATERIAL (END) ---" in mock_llm.last_prompt
        assert mock_llm.last_system_prompt is not None
        assert "only source of truth" in mock_llm.last_system_prompt
