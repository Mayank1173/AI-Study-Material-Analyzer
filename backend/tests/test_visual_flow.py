"""Phase 5 backend tests: visual evidence at the /api/chat boundary.

Verifies that when a student asks about a diagram/figure, the visual metadata
surfaces as an ordinary, correctly numbered ChatSource (with material id,
course id, filename, title, and page location) while normal text questions
never pull visual sources into the API response.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
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


@pytest.fixture()
def figure_pdf_path(tmp_path: Path) -> Path:
    icon = Image.new("RGB", (24, 24), (180, 80, 80))
    png = tmp_path / "fig.png"
    icon.save(str(png), format="PNG")

    path = tmp_path / "deadlock_figure.pdf"
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.drawString(72, 720, "Deadlock detection notes")
    pdf.drawString(72, 696, "The detection algorithm scans a wait-for graph for cycles.")
    pdf.showPage()
    pdf.drawString(72, 720, "Figure 1: Deadlock Detection Algorithm")
    pdf.drawString(72, 696, "The algorithm builds a wait-for graph and scans its edges.")
    pdf.drawImage(str(png), 100, 300, 60, 60)
    pdf.showPage()
    pdf.save()
    return path


class TestVisualFlow:
    def _index(self, user_id: str, tmp_path: Path, figure_pdf_path: Path):
        kb = get_knowledge_base(store_path=str(tmp_path / "visual_kb.db"))
        kb.index_material(
            figure_pdf_path,
            source_ref=SourceRef(
                material_id="m-fig",
                course_id="c-fig",
                original_filename="deadlock_figure.pdf",
                material_title="Deadlock Notes",
                source_type=".pdf",
            ),
            uploaded_by=user_id,
            chunk_size=1000,
            overlap=0,
        )
        return kb

    def test_visual_question_returns_visual_source(
        self, client, tmp_path, figure_pdf_path
    ) -> None:
        c, mock_llm = client
        user = _make_user("Alice", "alice@example.com")
        token = create_access_token(user.id)

        kb = self._index(str(user.id), tmp_path, figure_pdf_path)

        def override_kb():
            return kb

        app.dependency_overrides[chat_get_kb] = override_kb
        try:
            resp = c.post(
                "/api/chat",
                json={
                    "message": "which diagram shows the deadlock detection algorithm"
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            app.dependency_overrides.clear()
            kb.close()

        assert resp.status_code == 200
        data = resp.json()
        assert data["has_context"] is True
        assert set(data.keys()) == {"answer", "sources", "has_context"}
        assert "VISUAL SOURCE [Source" in mock_llm.last_prompt

        visual_sources = [
            s for s in data["sources"] if s["source_location"] == "page 2"
        ]
        assert len(visual_sources) == 1
        source = visual_sources[0]
        assert source["material_id"] == "m-fig"
        assert source["course_id"] == "c-fig"
        assert source["original_filename"] == "deadlock_figure.pdf"
        assert source["material_title"] == "Deadlock Notes"
        assert set(source.keys()) >= {
            "source_index",
            "material_id",
            "course_id",
            "material_title",
            "original_filename",
            "source_location",
            "score",
        }

    def test_normal_text_question_returns_no_visual_sources(
        self, client, tmp_path, figure_pdf_path
    ) -> None:
        c, mock_llm = client
        user = _make_user("Bella", "bella@example.com")
        token = create_access_token(user.id)

        kb = self._index(str(user.id), tmp_path, figure_pdf_path)

        def override_kb():
            return kb

        app.dependency_overrides[chat_get_kb] = override_kb
        try:
            resp = c.post(
                "/api/chat",
                json={"message": "what is deadlock detection"},
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            app.dependency_overrides.clear()
            kb.close()

        assert resp.status_code == 200
        data = resp.json()
        assert data["has_context"] is True
        assert "VISUAL SOURCE" not in mock_llm.last_prompt
        assert all(s["source_location"] != "page 2" for s in data["sources"])
        assert len(data["sources"]) == 1

    def test_visual_question_source_numbering_is_continuous(
        self, client, tmp_path, figure_pdf_path
    ) -> None:
        c, _ = client
        user = _make_user("Charlie", "charlie@example.com")
        token = create_access_token(user.id)

        kb = self._index(str(user.id), tmp_path, figure_pdf_path)

        def override_kb():
            return kb

        app.dependency_overrides[chat_get_kb] = override_kb
        try:
            resp = c.post(
                "/api/chat",
                json={"message": "which diagram shows the deadlock detection algorithm"},
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            app.dependency_overrides.clear()
            kb.close()

        assert resp.status_code == 200
        indices = [s["source_index"] for s in resp.json()["sources"]]
        assert indices == list(range(1, len(indices) + 1))