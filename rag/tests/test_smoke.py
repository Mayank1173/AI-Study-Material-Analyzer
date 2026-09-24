"""Real end-to-end smoke test: file -> Phase 1 -> embeddings -> SQLite -> query.

Uses the same real PDF/TXT fixtures as the extractor tests (reportlab authors a
real PDF; pypdf reads it back). The deterministic embedder is used so the test
runs offline, and the query shares enough lexical material with the document
that hashing-based similarity still ranks it correctly.
"""

from __future__ import annotations

from pathlib import Path

from rag.embeddings import DeterministicEmbedder
from rag.knowledge_base import KnowledgeBase
from rag.models import SourceRef
from rag.vectorstore import SqliteVectorStore


def test_full_pipeline_real_txt(tmp_path: Path) -> None:
    source = tmp_path / "biology.txt"
    source.write_text(
        "Photosynthesis converts light energy into chemical energy. "
        "The Calvin cycle fixes carbon dioxide into glucose in the stroma.",
        encoding="utf-8",
    )

    kb = KnowledgeBase(
        DeterministicEmbedder(dimension=128),
        SqliteVectorStore(str(tmp_path / "kb.db")),
    )
    try:
        count = kb.index_material(
            source,
            source_ref=SourceRef(
                material_id="smoke-txt",
                course_id="c-bio",
                original_filename=source.name,
                material_title="Photosynthesis",
            ),
            uploaded_by="student-1",
        )
        assert count >= 1

        results = kb.search(
            "carbon dioxide fixation", user_id="student-1", top_k=3
        )
        assert results
        assert results[0].material_id == "smoke-txt"
        assert "Calvin cycle" in results[0].text
        assert results[0].metadata.material_title == "Photosynthesis"
    finally:
        kb.close()


def test_full_pipeline_real_pdf(pdf_path: Path, tmp_path: Path) -> None:
    kb = KnowledgeBase(
        DeterministicEmbedder(dimension=128),
        SqliteVectorStore(str(tmp_path / "kb.pdf.db")),
    )
    try:
        count = kb.index_material(
            pdf_path,
            source_ref=SourceRef(
                material_id="smoke-pdf",
                course_id="c-bio",
                original_filename="lecture.pdf",
                material_title="Photosynthesis lecture",
            ),
            uploaded_by="student-1",
        )
        assert count >= 1

        results = kb.search("carbon dioxide", user_id="student-1", top_k=3)
        assert results
        assert results[0].material_id == "smoke-pdf"
        assert results[0].metadata.page in (1, 2)

        other = kb.search("carbon dioxide", user_id="student-2", top_k=3)
        assert other == []
    finally:
        kb.close()