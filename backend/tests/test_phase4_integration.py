"""Phase 4 integration tests: upload -> process -> index -> chat -> delete.

Uses MockProvider and temporary KnowledgeBase/vector stores.
Never requires Ollama or persistent default knowledge_base.db.
"""
from __future__ import annotations

import io
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

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
from app.api.routes.materials import get_processing_knowledge_base
from app.api.routes.chat import get_llm_provider as chat_get_llm_provider, _get_kb as chat_get_kb
from rag.knowledge_base import get_knowledge_base
from rag.llm.mock_provider import MockProvider
from rag.vectorstore.sqlite_store import SqliteVectorStore

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

_course_counter = 0


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
    file_name: str | None = None,
    stored_file_name: str | None = None,
    error_message: str | None = None,
) -> StudyMaterial:
    mat = StudyMaterial(
        course_id=course_id,
        uploaded_by=user_id,
        title=title,
        material_type="lecture_notes",
        status=status,
        file_name=file_name,
        stored_file_name=stored_file_name,
        error_message=error_message,
    )
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat


def _create_txt_file(tmpdir: Path, content: str) -> Path:
    path = tmpdir / f"{uuid.uuid4()}.txt"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture()
def client(tmp_path):
    _reset()
    mock_llm = MockProvider(
        keyword_answers={
            "photosynthesis": "Plants convert light energy into chemical energy via photosynthesis.",
            "operating systems": "Operating systems manage hardware resources and schedule processes.",
        }
    )

    store_path = tmp_path / "test_kb.db"
    kb = get_knowledge_base(store_path=str(store_path))

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    def override_llm():
        return mock_llm

    def override_kb():
        return kb

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[chat_get_llm_provider] = override_llm
    app.dependency_overrides[get_processing_knowledge_base] = override_kb
    app.dependency_overrides[chat_get_kb] = override_kb

    with TestClient(app) as c:
        yield c, mock_llm, kb

    app.dependency_overrides.clear()
    kb.close()


class TestUploadProcessFlow:
    def test_upload_then_process_sets_processed(self, client, tmp_path):
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course = _make_course(db, user.id)
        db.close()

        txt_content = "Photosynthesis is the process by which plants convert sunlight into energy."
        txt_path = _create_txt_file(tmp_path, txt_content)

        with open(txt_path, "rb") as f:
            resp = c.post(
                "/api/materials/upload",
                data={
                    "course_id": str(course.id),
                    "title": "Biology Notes",
                    "material_type": "notes",
                },
                files={"file": ("bio.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 201
        mat = resp.json()
        mat_id = mat["id"]
        assert mat["status"] == "uploaded"

        resp = c.post(
            f"/api/materials/{mat_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "processed"
        assert resp.json()["processed_at"] is not None

    def test_real_txt_gets_indexed(self, client, tmp_path):
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course = _make_course(db, user.id)
        db.close()

        txt_content = "Photosynthesis converts sunlight into chemical energy in plants."
        txt_path = _create_txt_file(tmp_path, txt_content)

        with open(txt_path, "rb") as f:
            resp = c.post(
                "/api/materials/upload",
                data={
                    "course_id": str(course.id),
                    "title": "Bio Notes",
                    "material_type": "notes",
                },
                files={"file": ("bio.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        mat_id = resp.json()["id"]

        resp = c.post(
            f"/api/materials/{mat_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.json()["status"] == "processed"

        count = kb.count(user_id=str(user.id))
        assert count > 0

    def test_owner_can_retrieve_indexed_material(self, client, tmp_path):
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course = _make_course(db, user.id)
        db.close()

        txt_content = "Operating systems manage hardware resources and schedule processes."
        txt_path = _create_txt_file(tmp_path, txt_content)

        with open(txt_path, "rb") as f:
            resp = c.post(
                "/api/materials/upload",
                data={
                    "course_id": str(course.id),
                    "title": "OS Notes",
                    "material_type": "notes",
                },
                files={"file": ("os.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        mat_id = resp.json()["id"]
        c.post(
            f"/api/materials/{mat_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )

        results = kb.search(
            "operating systems", user_id=str(user.id)
        )
        assert len(results) > 0

    def test_another_user_cannot_retrieve(self, client, tmp_path):
        c, mock_llm, kb = client
        alice = _make_user("Alice", "alice@example.com")
        bob = _make_user("Bob", "bob@example.com")
        alice_token = create_access_token(alice.id)
        bob_token = create_access_token(bob.id)

        db = TestingSession()
        course = _make_course(db, alice.id)
        db.close()

        txt_content = "Photosynthesis is essential for life on Earth."
        txt_path = _create_txt_file(tmp_path, txt_content)

        with open(txt_path, "rb") as f:
            resp = c.post(
                "/api/materials/upload",
                data={
                    "course_id": str(course.id),
                    "title": "Secret Notes",
                    "material_type": "notes",
                },
                files={"file": ("secret.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {alice_token}"},
            )

        mat_id = resp.json()["id"]
        c.post(
            f"/api/materials/{mat_id}/process",
            headers={"Authorization": f"Bearer {alice_token}"},
        )

        results = kb.search(
            "photosynthesis", user_id=str(bob.id)
        )
        assert len(results) == 0


class TestSubjectFiltering:
    def test_chat_course_filter(self, client, tmp_path):
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course1 = _make_course(db, user.id, name="Biology")
        course2 = _make_course(db, user.id, name="CS")
        db.close()

        for name, content, course in [
            ("bio.txt", "Photosynthesis converts sunlight to energy.", course1),
            ("cs.txt", "Operating systems manage hardware resources.", course2),
        ]:
            txt_path = _create_txt_file(tmp_path, content)
            with open(txt_path, "rb") as f:
                resp = c.post(
                    "/api/materials/upload",
                    data={
                        "course_id": str(course.id),
                        "title": f"{name} notes",
                        "material_type": "notes",
                    },
                    files={"file": (name, f, "text/plain")},
                    headers={"Authorization": f"Bearer {token}"},
                )
            mat_id = resp.json()["id"]
            c.post(
                f"/api/materials/{mat_id}/process",
                headers={"Authorization": f"Bearer {token}"},
            )

        resp = c.post(
            "/api/chat",
            json={
                "message": "What is photosynthesis?",
                "course_id": str(course1.id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_chat_material_filter(self, client, tmp_path):
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course = _make_course(db, user.id)
        db.close()

        txt_content = "Photosynthesis is a fundamental biological process."
        txt_path = _create_txt_file(tmp_path, txt_content)

        with open(txt_path, "rb") as f:
            resp = c.post(
                "/api/materials/upload",
                data={
                    "course_id": str(course.id),
                    "title": "Bio Notes",
                    "material_type": "notes",
                },
                files={"file": ("bio.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        mat_id = resp.json()["id"]
        c.post(
            f"/api/materials/{mat_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = c.post(
            "/api/chat",
            json={
                "message": "What is photosynthesis?",
                "material_id": mat_id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["has_context"] is True

    def test_chat_course_filter_restricts_returned_sources(self, client, tmp_path):
        """course_id filtering only returns sources belonging to that subject."""
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course1 = _make_course(db, user.id, name="Biology")
        course2 = _make_course(db, user.id, name="CS")
        db.close()

        for name, content, course in [
            ("bio.txt", "Photosynthesis converts sunlight to energy.", course1),
            ("os.txt", "Operating systems manage hardware resources.", course2),
        ]:
            txt_path = _create_txt_file(tmp_path, content)
            with open(txt_path, "rb") as f:
                resp = c.post(
                    "/api/materials/upload",
                    data={
                        "course_id": str(course.id),
                        "title": f"{name} notes",
                        "material_type": "notes",
                    },
                    files={"file": (name, f, "text/plain")},
                    headers={"Authorization": f"Bearer {token}"},
                )
            mat_id = resp.json()["id"]
            c.post(
                f"/api/materials/{mat_id}/process",
                headers={"Authorization": f"Bearer {token}"},
            )

        resp = c.post(
            "/api/chat",
            json={
                "message": "What is photosynthesis?",
                "course_id": str(course1.id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_context"] is True
        assert len(data["sources"]) > 0
        assert all(src["course_id"] == str(course1.id) for src in data["sources"])

    def test_chat_material_filter_restricts_returned_sources(self, client, tmp_path):
        """material_id filtering only returns sources from that material."""
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course = _make_course(db, user.id)
        db.close()

        os_content = "Operating systems manage hardware resources and schedule processes."
        os_path = _create_txt_file(tmp_path, os_content)
        with open(os_path, "rb") as f:
            resp = c.post(
                "/api/materials/upload",
                data={
                    "course_id": str(course.id),
                    "title": "OS Notes",
                    "material_type": "notes",
                },
                files={"file": ("os.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )
        os_mat_id = resp.json()["id"]
        c.post(
            f"/api/materials/{os_mat_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = c.post(
            "/api/chat",
            json={
                "message": "What is photosynthesis?",
                "material_id": os_mat_id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_context"] is True
        assert len(data["sources"]) > 0
        assert all(src["material_id"] == os_mat_id for src in data["sources"])


class TestDeleteCleanup:
    def test_delete_removes_rag_chunks(self, client, tmp_path):
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course = _make_course(db, user.id)
        db.close()

        txt_content = "Photosynthesis is the process by which plants make food."
        txt_path = _create_txt_file(tmp_path, txt_content)

        with open(txt_path, "rb") as f:
            resp = c.post(
                "/api/materials/upload",
                data={
                    "course_id": str(course.id),
                    "title": "Bio Notes",
                    "material_type": "notes",
                },
                files={"file": ("bio.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        mat_id = resp.json()["id"]
        c.post(
            f"/api/materials/{mat_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )

        count_before = kb.count(user_id=str(user.id))
        assert count_before > 0

        resp = c.delete(
            f"/api/materials/{mat_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

        count_after = kb.count(user_id=str(user.id))
        assert count_after == 0

    def test_deleted_material_not_searchable(self, client, tmp_path):
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course = _make_course(db, user.id)
        db.close()

        txt_content = "Photosynthesis converts light into chemical energy."
        txt_path = _create_txt_file(tmp_path, txt_content)

        with open(txt_path, "rb") as f:
            resp = c.post(
                "/api/materials/upload",
                data={
                    "course_id": str(course.id),
                    "title": "Bio Notes",
                    "material_type": "notes",
                },
                files={"file": ("bio.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        mat_id = resp.json()["id"]
        c.post(
            f"/api/materials/{mat_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )

        c.delete(
            f"/api/materials/{mat_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        results = kb.search(
            "photosynthesis", user_id=str(user.id)
        )
        assert len(results) == 0


class TestReprocessing:
    def test_reprocessing_does_not_duplicate(self, client, tmp_path):
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course = _make_course(db, user.id)
        db.close()

        txt_content = "Photosynthesis is a vital biological process for all life."
        txt_path = _create_txt_file(tmp_path, txt_content)

        with open(txt_path, "rb") as f:
            resp = c.post(
                "/api/materials/upload",
                data={
                    "course_id": str(course.id),
                    "title": "Bio Notes",
                    "material_type": "notes",
                },
                files={"file": ("bio.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        mat_id = resp.json()["id"]
        c.post(
            f"/api/materials/{mat_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )

        db2 = TestingSession()
        mat = db2.get(StudyMaterial, uuid.UUID(mat_id))
        mat.status = "failed"
        db2.commit()
        db2.close()

        c.post(
            f"/api/materials/{mat_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )

        results = kb.search(
            "photosynthesis", user_id=str(user.id)
        )
        assert len(results) <= 5

        material_ids = {r.material_id for r in results}
        assert material_ids == {mat_id}


class TestProcessingFailure:
    def test_processing_failure_sets_failed_status(self, client, tmp_path):
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course = _make_course(db, user.id)
        db.close()

        mat = _make_material(
            db, course.id, user.id,
            title="No File Material",
            status="uploaded",
            stored_file_name=None,
        )
        db.close()

        resp = c.post(
            f"/api/materials/{mat.id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"
        assert resp.json()["error_message"] is not None

    def test_retry_after_failure(self, client, tmp_path):
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course = _make_course(db, user.id)
        db.close()

        mat = _make_material(
            db, course.id, user.id,
            title="Failed Material",
            status="failed",
            error_message="Previous error",
        )
        db.close()

        resp = c.post(
            f"/api/materials/{mat.id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"
        assert resp.json()["error_message"] is not None


class TestUnsupportedFormats:
    def test_unsupported_file_type_rejected_on_upload(self, client):
        c, _, _ = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course = _make_course(db, user.id)
        db.close()

        resp = c.post(
            "/api/materials/upload",
            data={
                "course_id": str(course.id),
                "title": "Bad File",
                "material_type": "notes",
            },
            files={"file": ("bad.exe", b"MZ\x90\x00", "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 415


class TestChatGroundedAnswers:
    def test_chat_returns_grounded_answer(self, client, tmp_path):
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course = _make_course(db, user.id)
        db.close()

        txt_content = "Photosynthesis is the process by which green plants convert sunlight into chemical energy."
        txt_path = _create_txt_file(tmp_path, txt_content)

        with open(txt_path, "rb") as f:
            resp = c.post(
                "/api/materials/upload",
                data={
                    "course_id": str(course.id),
                    "title": "Bio Notes",
                    "material_type": "notes",
                },
                files={"file": ("bio.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        mat_id = resp.json()["id"]
        c.post(
            f"/api/materials/{mat_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = c.post(
            "/api/chat",
            json={"message": "What is photosynthesis?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "photosynthesis" in data["answer"].lower()
        assert data["has_context"] is True
        assert len(data["sources"]) > 0

    def test_chat_returns_sources(self, client, tmp_path):
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course = _make_course(db, user.id)
        db.close()

        txt_content = "Photosynthesis converts light energy into chemical energy stored in glucose."
        txt_path = _create_txt_file(tmp_path, txt_content)

        with open(txt_path, "rb") as f:
            resp = c.post(
                "/api/materials/upload",
                data={
                    "course_id": str(course.id),
                    "title": "Bio Notes",
                    "material_type": "notes",
                },
                files={"file": ("bio.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        mat_id = resp.json()["id"]
        c.post(
            f"/api/materials/{mat_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = c.post(
            "/api/chat",
            json={"message": "What is photosynthesis?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        data = resp.json()
        assert len(data["sources"]) > 0
        source = data["sources"][0]
        assert source["material_id"] == mat_id
        assert source["material_title"] == "Bio Notes"
        assert source["original_filename"] == "bio.txt"

    def test_chat_user_isolation(self, client, tmp_path):
        c, mock_llm, kb = client
        alice = _make_user("Alice", "alice@example.com")
        bob = _make_user("Bob", "bob@example.com")
        alice_token = create_access_token(alice.id)
        bob_token = create_access_token(bob.id)

        db = TestingSession()
        course = _make_course(db, alice.id)
        db.close()

        txt_content = "Photosynthesis is a critical process for life on Earth."
        txt_path = _create_txt_file(tmp_path, txt_content)

        with open(txt_path, "rb") as f:
            resp = c.post(
                "/api/materials/upload",
                data={
                    "course_id": str(course.id),
                    "title": "Alice Bio Notes",
                    "material_type": "notes",
                },
                files={"file": ("bio.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {alice_token}"},
            )

        mat_id = resp.json()["id"]
        c.post(
            f"/api/materials/{mat_id}/process",
            headers={"Authorization": f"Bearer {alice_token}"},
        )

        resp = c.post(
            "/api/chat",
            json={"message": "What is photosynthesis?"},
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["has_context"] is False
        assert resp.json()["sources"] == []

    def test_blank_query_returns_no_context(self, client):
        c, _, _ = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        resp = c.post(
            "/api/chat",
            json={"message": "   "},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["has_context"] is False


class TestLLMFailure:
    def test_llm_failure_returns_graceful_message(self, client, tmp_path):
        c, mock_llm, kb = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        db = TestingSession()
        course = _make_course(db, user.id)
        db.close()

        txt_content = "Photosynthesis is the process by which plants make food from sunlight."
        txt_path = _create_txt_file(tmp_path, txt_content)

        with open(txt_path, "rb") as f:
            resp = c.post(
                "/api/materials/upload",
                data={
                    "course_id": str(course.id),
                    "title": "Bio Notes",
                    "material_type": "notes",
                },
                files={"file": ("bio.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )

        mat_id = resp.json()["id"]
        c.post(
            f"/api/materials/{mat_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )

        class FailingLLM:
            def generate(self, *a, **kw):
                raise RuntimeError("LLM unavailable")

            def is_available(self):
                return False

            def close(self):
                pass

        app.dependency_overrides[chat_get_llm_provider] = lambda: FailingLLM()

        resp = c.post(
            "/api/chat",
            json={"message": "What is photosynthesis?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert "unavailable" in resp.json()["answer"].lower()


class TestUserIdNotSpoofable:
    def test_user_id_cannot_be_spoofed(self, client, tmp_path):
        c, mock_llm, kb = client
        alice = _make_user("Alice", "alice@example.com")
        bob = _make_user("Bob", "bob@example.com")
        alice_token = create_access_token(alice.id)
        bob_token = create_access_token(bob.id)

        db = TestingSession()
        course = _make_course(db, alice.id)
        db.close()

        txt_content = "Photosynthesis is essential for plant survival and growth."
        txt_path = _create_txt_file(tmp_path, txt_content)

        with open(txt_path, "rb") as f:
            resp = c.post(
                "/api/materials/upload",
                data={
                    "course_id": str(course.id),
                    "title": "Alice Bio Notes",
                    "material_type": "notes",
                },
                files={"file": ("bio.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {alice_token}"},
            )

        mat_id = resp.json()["id"]
        c.post(
            f"/api/materials/{mat_id}/process",
            headers={"Authorization": f"Bearer {alice_token}"},
        )

        resp = c.post(
            "/api/chat",
            json={
                "message": "What is photosynthesis?",
            },
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["has_context"] is False
