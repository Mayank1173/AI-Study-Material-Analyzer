"""Tests for the /api/chat/summary endpoint."""

from __future__ import annotations

import uuid
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models import Course, StudyMaterial, User
from main import app
from rag.llm.mock_provider import MockProvider
from app.api.routes.chat import get_llm_provider as chat_get_llm_provider

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


def _reset() -> None:
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


def _create_course(client, headers, name="Biology", code="BIO101") -> dict:
    response = client.post(
        "/api/courses",
        json={"name": name, "code": code},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _upload_and_process(
    client,
    headers,
    course_id,
    *,
    title="Biology Notes",
    content=None,
) -> dict:
    payload = content or (
        "Biology studies living organisms. "
        "Photosynthesis converts light energy into chemical energy. "
        "The Calvin cycle fixes carbon dioxide into glucose in the stroma. "
        "Mitosis produces two identical daughter cells."
    )
    response = client.post(
        "/api/materials/upload",
        data={
            "course_id": course_id,
            "title": title,
            "material_type": "notes",
        },
        files={"file": ("notes.txt", BytesIO(payload.encode()), "text/plain")},
        headers=headers,
    )
    assert response.status_code == 201
    material = response.json()

    process = client.post(
        f"/api/materials/{material['id']}/process", headers=headers
    )
    assert process.status_code == 200
    assert process.json()["status"] == "processed"
    return material


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Client with a deterministic mock LLM and an isolated RAG store."""
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    _reset()

    mock_llm = MockProvider(
        keyword_answers={
            "biology": "Study summary: biology concepts, topics, and definitions from the material.",
            "operating systems": "Study summary: operating systems concepts from the material.",
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
    get_settings.cache_clear()


class TestSummaryAuthentication:
    def test_requires_auth(self, client) -> None:
        c, _ = client
        resp = c.post("/api/chat/summary", json={"course_id": str(uuid.uuid4())})
        assert resp.status_code in (401, 403)

    def test_rejects_invalid_token(self, client) -> None:
        c, _ = client
        resp = c.post(
            "/api/chat/summary",
            json={},
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401

    def test_rejects_invalid_course_id(self, client) -> None:
        c, _ = client
        user = _make_user("Alice", "alice@example.com")
        resp = c.post(
            "/api/chat/summary",
            json={"course_id": "not-a-uuid"},
            headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


class TestSummaryGeneration:
    def test_generates_summary_with_sources(
        self, client, tmp_path, monkeypatch
    ) -> None:
        c, mock_llm = client
        user = _make_user("Alice", "alice@example.com")
        headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
        course = _create_course(c, headers, name="Biology")
        _upload_and_process(c, headers, course["id"])

        resp = c.post(
            "/api/chat/summary",
            json={"course_id": course["id"]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "study summary: biology" in data["summary"].lower()
        assert data["has_context"] is True
        assert isinstance(data["sources"], list)
        assert len(data["sources"]) >= 1
        src = data["sources"][0]
        assert src["course_id"] == course["id"]
        assert src["material_title"] == "Biology Notes"

    def test_subject_filter_limits_sources_to_course(
        self, client, tmp_path, monkeypatch
    ) -> None:
        c, _ = client
        user = _make_user("Alice", "alice@example.com")
        headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
        bio = _create_course(c, headers, name="Biology", code="BIO101")
        os = _create_course(c, headers, name="Operating Systems", code="OS101")
        _upload_and_process(c, headers, bio["id"])
        _upload_and_process(
            c,
            headers,
            os["id"],
            title="OS Notes",
            content=(
                "Operating systems schedule processes using algorithms like "
                "round-robin. The ready queue holds runnable processes."
            ),
        )

        resp = c.post(
            "/api/chat/summary",
            json={"course_id": bio["id"]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_context"] is True
        assert len(data["sources"]) >= 1
        assert all(s["course_id"] == str(bio["id"]) for s in data["sources"])


class TestSummaryNoMaterial:
    def test_no_material_returns_no_context_message(self, client) -> None:
        c, mock_llm = client
        user = _make_user("Alice", "alice@example.com")
        headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
        course = _create_course(c, headers, name="Biology")

        resp = c.post(
            "/api/chat/summary",
            json={"course_id": course["id"]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_context"] is False
        assert data["sources"] == []
        assert "no processed study material" in data["summary"].lower()
        assert mock_llm.call_count == 0


class TestSummaryOwnership:
    def test_another_users_material_cannot_be_retrieved(
        self, client, tmp_path, monkeypatch
    ) -> None:
        c, _ = client
        alice = _make_user("Alice", "alice@example.com")
        bob = _make_user("Bob", "bob@example.com")
        alice_headers = {"Authorization": f"Bearer {create_access_token(alice.id)}"}
        bob_headers = {"Authorization": f"Bearer {create_access_token(bob.id)}"}

        course = _create_course(c, alice_headers, name="Biology")
        _upload_and_process(c, alice_headers, course["id"])

        resp = c.post(
            "/api/chat/summary",
            json={"course_id": course["id"]},
            headers=bob_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_context"] is False
        assert data["sources"] == []
        assert "no processed study material" in data["summary"].lower()


class TestSummaryLLMFailure:
    def test_llm_failure_returns_safe_message(
        self, client, tmp_path, monkeypatch
    ) -> None:
        c, _ = client
        user = _make_user("Alice", "alice@example.com")
        headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
        course = _create_course(c, headers, name="Biology")
        _upload_and_process(c, headers, course["id"])

        class FailingLLM(MockProvider):
            def generate(self, *args, **kwargs):  # type: ignore[override]
                raise RuntimeError("LLM crashed")

        def override_llm():
            return FailingLLM()

        app.dependency_overrides[chat_get_llm_provider] = override_llm

        resp = c.post(
            "/api/chat/summary",
            json={"course_id": course["id"]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_context"] is True
        assert "temporarily unavailable" in data["summary"].lower()
        assert len(data["sources"]) >= 1