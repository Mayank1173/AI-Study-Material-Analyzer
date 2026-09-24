"""Phase 4 backend tests: advanced source reasoning at the /api/chat boundary.

Verifies that the API exposes well-aligned source attribution, lets several
retrieved sources combine into one grounded answer, presents conflicting
material per source, never fabricates [Source N] citations, and keeps the
ownership scoping intact end to end.
"""

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
from app.models import User
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


@pytest.fixture()
def client():
    _reset()
    mock_llm = MockProvider()

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


def _citations(prompt: str) -> str:
    prefix = "Available source numbers for citations:"
    start = prompt.index(prefix) + len(prefix)
    end = prompt.index(".", start)
    return prompt[start:end].strip()


class TestMultiSourceSynthesis:
    def test_two_sources_combine_into_one_answer(self, client, tmp_path) -> None:
        c, mock_llm = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        (tmp_path / "a.txt").write_text(
            "TCP is a connection-oriented transport protocol that guarantees delivery.",
            encoding="utf-8",
        )
        (tmp_path / "b.txt").write_text(
            "UDP is a connectionless protocol that favours speed over reliability.",
            encoding="utf-8",
        )

        def override_kb():
            return kb

        kb = get_knowledge_base(store_path=str(tmp_path / "kb.db"))
        kb.index_material(
            tmp_path / "a.txt",
            source_ref=SourceRef(
                material_id="m-tcp",
                course_id="c-net",
                original_filename="a.txt",
                material_title="TCP Notes",
            ),
            uploaded_by=str(user.id),
        )
        kb.index_material(
            tmp_path / "b.txt",
            source_ref=SourceRef(
                material_id="m-udp",
                course_id="c-net",
                original_filename="b.txt",
                material_title="UDP Notes",
            ),
            uploaded_by=str(user.id),
        )

        app.dependency_overrides[chat_get_kb] = override_kb
        try:
            resp = c.post(
                "/api/chat",
                json={"message": "compare TCP and UDP"},
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            app.dependency_overrides.clear()
            kb.close()

        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {"answer", "sources", "has_context"}
        assert data["has_context"] is True
        assert len(data["sources"]) >= 2
        assert [s["source_index"] for s in data["sources"]] == [1, 2]
        prompt = mock_llm.last_prompt
        assert "SOURCE A:" in prompt
        assert "SOURCE B:" in prompt
        assert "tcp is a connection-oriented" in prompt.lower()
        assert "udp is a connectionless" in prompt.lower()
        assert "Available source numbers for citations: [Source 1] [Source 2]." in prompt


class TestSourceAttribution:
    def test_public_source_fields_are_well_formed(self, client, tmp_path) -> None:
        c, _ = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        (tmp_path / "a.txt").write_text(
            "TCP is a connection-oriented transport protocol.",
            encoding="utf-8",
        )
        (tmp_path / "b.txt").write_text(
            "UDP is a connectionless protocol.",
            encoding="utf-8",
        )

        kb = get_knowledge_base(store_path=str(tmp_path / "kb.db"))
        kb.index_material(
            tmp_path / "a.txt",
            source_ref=SourceRef(
                material_id="m-tcp",
                course_id="c-net",
                original_filename="a.txt",
                material_title="TCP Notes",
            ),
            uploaded_by=str(user.id),
        )
        kb.index_material(
            tmp_path / "b.txt",
            source_ref=SourceRef(
                material_id="m-udp",
                course_id="c-net",
                original_filename="b.txt",
                material_title="UDP Notes",
            ),
            uploaded_by=str(user.id),
        )

        app.dependency_overrides[chat_get_kb] = lambda: kb
        try:
            resp = c.post(
                "/api/chat",
                json={"message": "TCP and UDP"},
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            app.dependency_overrides.clear()
            kb.close()

        assert resp.status_code == 200
        sources = resp.json()["sources"]
        expected_keys = {
            "source_index",
            "material_id",
            "course_id",
            "material_title",
            "original_filename",
            "source_location",
            "score",
        }
        assert sources
        for source in sources:
            assert set(source.keys()) == expected_keys
        titles = [s["material_title"] for s in sources]
        assert "TCP Notes" in titles
        assert "UDP Notes" in titles
        assert all(s["course_id"] == "c-net" for s in sources)


class TestConflictPresentation:
    def test_conflicting_materials_both_reach_the_model(self, client, tmp_path) -> None:
        c, mock_llm = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        (tmp_path / "notes.txt").write_text(
            "Deadlock prevention breaks the circular wait condition.",
            encoding="utf-8",
        )
        (tmp_path / "slides.txt").write_text(
            "Deadlock prevention is not used; avoidance is used instead.",
            encoding="utf-8",
        )

        kb = get_knowledge_base(store_path=str(tmp_path / "kb.db"))
        kb.index_material(
            tmp_path / "notes.txt",
            source_ref=SourceRef(
                material_id="m-notes",
                course_id="c-os",
                original_filename="notes.txt",
                material_title="OS Notes",
            ),
            uploaded_by=str(user.id),
        )
        kb.index_material(
            tmp_path / "slides.txt",
            source_ref=SourceRef(
                material_id="m-slides",
                course_id="c-os",
                original_filename="slides.txt",
                material_title="OS Slides",
            ),
            uploaded_by=str(user.id),
        )

        app.dependency_overrides[chat_get_kb] = lambda: kb
        try:
            resp = c.post(
                "/api/chat",
                json={"message": "How is deadlock prevented?"},
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            app.dependency_overrides.clear()
            kb.close()

        assert resp.status_code == 200
        data = resp.json()
        assert data["has_context"] is True
        assert set(data.keys()) == {"answer", "sources", "has_context"}
        assert len(data["sources"]) >= 2
        prompt = mock_llm.last_prompt
        assert "breaks the circular wait condition" in prompt
        assert "avoidance is used instead" in prompt
        assert "Material: OS Notes" in prompt
        assert "Material: OS Slides" in prompt

    def test_conflict_instructions_reach_the_model(self, client, tmp_path) -> None:
        c, mock_llm = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        (tmp_path / "n.txt").write_text(
            "Deadlock prevention breaks the circular wait condition.",
            encoding="utf-8",
        )
        (tmp_path / "s.txt").write_text(
            "Deadlock prevention is not used; avoidance is used instead.",
            encoding="utf-8",
        )

        kb = get_knowledge_base(store_path=str(tmp_path / "kb.db"))
        for name, mid, title in (
            ("n.txt", "m-notes", "OS Notes"),
            ("s.txt", "m-slides", "OS Slides"),
        ):
            kb.index_material(
                tmp_path / name,
                source_ref=SourceRef(
                    material_id=mid,
                    course_id="c-os",
                    original_filename=name,
                    material_title=title,
                ),
                uploaded_by=str(user.id),
            )

        app.dependency_overrides[chat_get_kb] = lambda: kb
        try:
            resp = c.post(
                "/api/chat",
                json={"message": "deadlock prevention"},
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            app.dependency_overrides.clear()
            kb.close()

        assert resp.status_code == 200
        system = (mock_llm.last_system_prompt or "").lower()
        assert "do not silently choose one as correct" in system
        assert "authoritative" in system
        assert "never invent a source" in system


class TestCitationIntegrity:
    def test_citation_numbers_match_retrieved_sources(self, client, tmp_path) -> None:
        c, mock_llm = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        (tmp_path / "a.txt").write_text(
            "TCP is a connection-oriented transport protocol.",
            encoding="utf-8",
        )
        (tmp_path / "b.txt").write_text(
            "UDP is a connectionless protocol.",
            encoding="utf-8",
        )

        kb = get_knowledge_base(store_path=str(tmp_path / "kb.db"))
        kb.index_material(
            tmp_path / "a.txt",
            source_ref=SourceRef(
                material_id="m-tcp",
                course_id="c-net",
                original_filename="a.txt",
                material_title="TCP Notes",
            ),
            uploaded_by=str(user.id),
        )
        kb.index_material(
            tmp_path / "b.txt",
            source_ref=SourceRef(
                material_id="m-udp",
                course_id="c-net",
                original_filename="b.txt",
                material_title="UDP Notes",
            ),
            uploaded_by=str(user.id),
        )

        app.dependency_overrides[chat_get_kb] = lambda: kb
        try:
            resp = c.post(
                "/api/chat",
                json={"message": "TCP and UDP"},
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            app.dependency_overrides.clear()
            kb.close()

        assert resp.status_code == 200
        data = resp.json()
        assert _citations(mock_llm.last_prompt) == "[Source 1] [Source 2]"
        assert "[Source 3]" not in _citations(mock_llm.last_prompt)
        assert len(data["sources"]) == 2
        assert [s["source_index"] for s in data["sources"]] == [1, 2]


class TestOwnershipIsolation:
    def test_other_users_material_is_never_a_source(self, client, tmp_path) -> None:
        c, _ = client
        alice = _make_user("Alice", "alice@example.com")
        bob = _make_user("Bob", "bob@example.com")

        (tmp_path / "a.txt").write_text(
            "TCP is a connection-oriented transport protocol.",
            encoding="utf-8",
        )

        kb = get_knowledge_base(store_path=str(tmp_path / "kb.db"))
        kb.index_material(
            tmp_path / "a.txt",
            source_ref=SourceRef(
                material_id="m-tcp",
                course_id="c-net",
                original_filename="a.txt",
                material_title="TCP Notes",
            ),
            uploaded_by=str(alice.id),
        )

        app.dependency_overrides[chat_get_kb] = lambda: kb
        try:
            resp = c.post(
                "/api/chat",
                json={"message": "What is TCP?"},
                headers={"Authorization": f"Bearer {create_access_token(bob.id)}"},
            )
        finally:
            app.dependency_overrides.clear()
            kb.close()

        assert resp.status_code == 200
        data = resp.json()
        assert data["has_context"] is False
        assert data["sources"] == []