from __future__ import annotations

import logging
import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.api.routes.chat import get_llm_provider
from app.db.session import get_db
from app.models import Course, StudyMaterial, User
from app.schemas.pyq import (
    PyqAnalysisRequest,
    PyqAnalysisResponse,
    PyqAnswerRequest,
    PyqAnswerResponse,
    PyqAnswerSource,
    PyqQuestion,
)
from app.services import study_material_service
from app.core.storage import resolve_file_path
from app.services.pyq_service import PyqAnalyzer
from rag.knowledge_base import KnowledgeBase, get_knowledge_base
from rag.llm import LLMProvider
from rag.pyq_answer import PyqAnswerGenerationError, answer_pyq_question

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pyqs", tags=["PYQs"])


def get_kb() -> KnowledgeBase:
    try:
        kb = get_knowledge_base()
        yield kb
    finally:
        try:
            kb.close()
        except Exception:
            pass


def _stored_reference(material: StudyMaterial) -> str | None:
    """Return the stored-file reference to read from disk, if any.

    Uploaded files record ``stored_file_name``; ``file_path`` is only populated
    for legacy/URL records. Processing already reads ``stored_file_name``, so
    analysis must do the same or it silently skips every uploaded paper.
    """
    return material.stored_file_name or material.file_path


@router.post("/analyze", response_model=PyqAnalysisResponse)
def analyze_pyqs(
    body: PyqAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    kb: KnowledgeBase = Depends(get_kb),
):
    try:
        analyzer = PyqAnalyzer(knowledge_base=kb)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize analyzer: {str(e)}",
        )

# Resolve exactly the requested files. A requested file that is missing or
    # owned by someone else is reported as a failure rather than silently
    # dropped, so the frontend can tell the user which papers were not used.
    materials: list[StudyMaterial] = []
    failed_files: list[str] = []
    if body.file_ids:
        for fid in body.file_ids:
            label = fid
            try:
                m = study_material_service.get_study_material(db, uuid.UUID(fid))
                label = m.file_name or fid
                if m.uploaded_by != current_user.id:
                    failed_files.append(label)
                    continue
                if not _stored_reference(m) or not m.file_name:
                    failed_files.append(label)
                    continue
                materials.append(m)
            except Exception:
                failed_files.append(label)
    else:
        try:
            total, items = study_material_service.list_study_materials(
                db, user=current_user, page=1, page_size=100
            )
            for m in items:
                if _stored_reference(m) and m.file_name:
                    materials.append(m)
        except Exception:
            pass

    question_freq = defaultdict(lambda: {
        'question': '',
        'years': set(),
        'files': set(),
        'count': 0,
        'marks': None,
        'unit': None,
    })

    analyzed_files: list[str] = []
    for m in materials:
        reference = _stored_reference(m)
        try:
            file_path = resolve_file_path(reference)
            result = analyzer.analyze_document(str(file_path), m.file_name)
        except Exception:
            # Unreadable/corrupt paper: report it, continue with the rest.
            failed_files.append(m.file_name or str(m.id))
            continue
        if not result.get('ok'):
            # Extraction failed for this paper specifically.
            failed_files.append(m.file_name or str(m.id))
            continue
        if m.file_name:
            analyzed_files.append(m.file_name)
        # Real per-question metadata (marks, unit, year) when the paper states it.
        meta_by_text = {
            entry['text']: entry for entry in result.get('question_meta', [])
        }
        for q in result.get('questions', []):
            key = q[:200].lower()
            if not question_freq[key]['question']:
                question_freq[key]['question'] = q
            question_freq[key]['count'] += 1
            if m.file_name:
                question_freq[key]['files'].add(m.file_name)
            meta = meta_by_text.get(q, {})
            if meta.get('marks') is not None and question_freq[key]['marks'] is None:
                question_freq[key]['marks'] = meta['marks']
            if meta.get('unit') and not question_freq[key]['unit']:
                question_freq[key]['unit'] = meta['unit']
            if meta.get('year'):
                question_freq[key]['years'].add(meta['year'])

    all_questions = []
    for key, info in question_freq.items():
        freq = info['count']
        importance = 'High' if freq >= 2 else 'Medium'
        years = sorted(y for y in info['years'] if y)
        all_questions.append({
            'question': info['question'],
            'years_appeared': years,
            'unit': info['unit'],
            'marks': info['marks'],
            'importance': importance,
            'frequency': freq,
            'files': sorted(list(info['files'])),
            'answer': None,
        })

    if len(all_questions) > 1 and kb is not None:
        similar = analyzer.find_similar_questions(
            [q['question'] for q in all_questions]
        )
        merged = [False] * len(all_questions)
        for i, j, score in similar:
            if merged[i] or merged[j]:
                continue
            # Fold the weaker occurrence into the stronger one, carrying over
            # its frequency, files, years, marks and unit.
            keep, drop = (i, j) if all_questions[i]['frequency'] >= all_questions[j]['frequency'] else (j, i)
            target = all_questions[keep]
            other = all_questions[drop]
            target['frequency'] += other['frequency']
            target['files'] = sorted(set(target['files'] + other['files']))
            target['years_appeared'] = sorted(
                set(target['years_appeared'] or []) | set(other['years_appeared'] or [])
            )
            if target['marks'] is None:
                target['marks'] = other['marks']
            if not target['unit']:
                target['unit'] = other['unit']
            target['importance'] = 'High'
            merged[drop] = True

        all_questions = [
            q for idx, q in enumerate(all_questions) if not merged[idx]
        ]

    ranked = analyzer.rank_questions(all_questions, body.num_questions)

    questions_out = []
    for rq in ranked:
        questions_out.append(
            PyqQuestion(
                question=rq['question'],
                years_appeared=rq.get('years_appeared', ''),
                unit=rq.get('unit'),
                marks=rq.get('marks'),
                importance=rq.get('importance', 'Medium'),
                frequency=rq.get('frequency', 0),
                files=rq.get('files', []),
                answer=rq.get('answer'),
            )
        )

    high_count = sum(1 for q in ranked if q.get('importance') == 'High')
    repeated_count = sum(1 for q in ranked if q.get('frequency', 0) >= 2)

    return PyqAnalysisResponse(
        questions=questions_out,
        total_questions=len(all_questions),
        repeated=repeated_count,
        top_priority=high_count,
        analyzed_files=analyzed_files,
        failed_files=failed_files,
        summary={
            'papers_analyzed': len(analyzed_files),
            'papers_failed': len(failed_files),
            'questions_found': len(all_questions),
        },
    )


def _to_answer_source(src) -> PyqAnswerSource:
    return PyqAnswerSource(
        source_index=src.source_index,
        material_id=src.material_id,
        course_id=src.course_id,
        material_title=src.material_title,
        original_filename=src.original_filename,
        source_location=src.source_location,
        score=src.score,
    )


@router.post("/answer", response_model=PyqAnswerResponse)
def generate_pyq_answer(
    body: PyqAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    kb: KnowledgeBase = Depends(get_kb),
    llm: LLMProvider = Depends(get_llm_provider),
) -> PyqAnswerResponse:
    """Generate an exam answer for one previous-year question.

    Reuses the existing RAG pipeline (owner-scoped embedding search over the
    shared vector store -> context builder -> existing LLM provider), so there
    is no second retrieval system. The answer is shaped by the selected marks,
    answer format and course.

    Grounding:
    - When sufficiently relevant study material is retrieved, the answer is
      grounded in it and ``has_context`` is ``True``.
    - When nothing relevant is found, the question is still answered from the
      model's general knowledge and ``has_context`` is ``False`` so the frontend
      can tell the user the answer is not from their material.

    Security (mirrors /api/chat):
    - Authentication is required (JWT Bearer token).
    - ``user_id`` is taken from the JWT, never from the request body.
    - ``course_id`` can only narrow the authenticated user's own index.
    """
    user_id = str(current_user.id)

    course_name = body.course_name
    if body.course_id is not None:
        course = db.get(Course, body.course_id)
        if course is not None:
            course_name = course.name

    styles = body.styles.model_dump() if body.styles is not None else None

    try:
        result = answer_pyq_question(
            kb,
            llm,
            question=body.question,
            user_id=user_id,
            course_id=str(body.course_id) if body.course_id is not None else None,
            course_name=course_name,
            marks=body.marks,
            answer_format=body.answer_format,
            styles=styles,
        )
    except PyqAnswerGenerationError as exc:
        # A failed generation must not become a 200 with an error string in the
        # answer field: the UI would render it as a real model answer.
        if exc.timed_out:
            logger.error("PYQ answer timed out for user=%s: %s", user_id, exc)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=(
                    "The language model took too long to answer this question. "
                    "Please try again or choose a shorter answer format."
                ),
            ) from exc
        logger.error("PYQ answer generation failed for user=%s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception:
        logger.exception("PYQ answer generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate an answer. Please try again later.",
        )

    return PyqAnswerResponse(
        answer=result.answer,
        has_context=result.has_context,
        sources=[_to_answer_source(s) for s in result.sources],
        model=result.model,
        marks=result.marks,
        answer_format=result.answer_format,
        course_name=result.course_name,
    )
