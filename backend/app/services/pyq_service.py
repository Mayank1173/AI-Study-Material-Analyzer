from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import PurePosixPath
from typing import Any

from rag.extractors import supports_extension
from rag.extraction import extract_document

# Marks written as "(10 marks)", "[5 M]", "(10M)", "(2 mark)".
_MARKS_PATTERN = re.compile(
    r"[\(\[]\s*(\d{1,2})\s*(?:marks?|m\.?)\s*[\)\]]", re.IGNORECASE
)
# Marks written as a trailing bracket with only a number, e.g. "Explain TCP [10]".
_MARKS_BRACKET_ONLY = re.compile(r"[\(\[]\s*(\d{1,2})\s*[\)\]]\s*$")
# Unit / module headings and inline mentions: "Unit 3", "UNIT-II", "Module 2".
_UNIT_PATTERN = re.compile(
    r"\b(?:unit|module|section)\s*[-:]?\s*([0-9]{1,2}|[ivx]{1,4})\b",
    re.IGNORECASE,
)
# Digit-boundary years. A leading ``\b`` would fail on names like
# "DCCN_2023.pdf", because "_" and "2" are both word characters.
_YEAR_PATTERN = re.compile(r"(?<!\d)(19[5-9]\d|20[0-4]\d)(?!\d)")
# Roman-numeral question numbering: "iv. Explain ..." as used in many papers.
_ROMAN_QUESTION_PATTERN = re.compile(r"^\s*([ivx]{1,6})[\.\)]\s+", re.IGNORECASE)
# A line that *is* a unit/module heading, e.g. "Unit 1", "UNIT-II:", "Module 3".
_UNIT_HEADING_PATTERN = re.compile(
    r"^\s*(?:unit|module|section)\s*[-:]?\s*([0-9]{1,2}|[ivx]{1,4})\b",
    re.IGNORECASE,
)
_ROMANS = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8,
    "ix": 9, "x": 10, "xi": 11, "xii": 12,
}


class PyqAnalyzer:
    def __init__(self, knowledge_base=None):
        self.knowledge_base = knowledge_base

    @staticmethod
    def extract_marks(text: str) -> int | None:
        """Pull the mark value out of a question line, if it is stated."""
        for pattern in (_MARKS_PATTERN, _MARKS_BRACKET_ONLY):
            match = pattern.search(text)
            if match:
                try:
                    value = int(match.group(1))
                except ValueError:
                    continue
                if 1 <= value <= 100:
                    return value
        return None

    @staticmethod
    def extract_unit(text: str) -> str | None:
        """Pull a unit/module reference from a question line, if stated."""
        match = _UNIT_PATTERN.search(text)
        if not match:
            return None
        value = match.group(1)
        if value.isdigit():
            return f"Unit {int(value)}"
        return f"Unit {value.upper()}"

    @staticmethod
    def extract_paper_year(text: str, filename: str | None) -> str | None:
        """Determine the exam year for a paper.

        The filename is the strongest signal (e.g. ``DCCN_2024.pdf``); otherwise
        the most frequently mentioned year near the top of the paper is used.
        """
        if filename:
            match = _YEAR_PATTERN.search(filename)
            if match:
                return match.group(1)
        if text:
            head = "\n".join(text.splitlines()[:40])
            years = _YEAR_PATTERN.findall(head)
            if years:
                return Counter(years).most_common(1)[0][0]
        return None

    def extract_questions_with_meta(
        self, text: str, year: str | None = None
    ) -> list[dict[str, Any]]:
        """Extract questions with their marks, unit and paper year.

        Units are usually section *headings* rather than part of the question
        line, so the scan tracks the most recent unit heading and applies it to
        the questions that follow.
        """
        if not text:
            return []

        entries: list[dict[str, Any]] = []
        current_unit: str | None = None

        def add(raw: str) -> None:
            question = re.sub(r'\s+', ' ', raw).strip()
            if not question:
                return
            entries.append(
                {
                    'text': question,
                    'marks': self.extract_marks(question),
                    'unit': current_unit or self.extract_unit(question),
                    'year': year,
                }
            )

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            # A unit/module heading sets the context and is never a question.
            if _UNIT_HEADING_PATTERN.match(stripped):
                current_unit = self.extract_unit(stripped) or current_unit
                continue

            if re.match(r'^\s*(\d+[\.\)\:])\s+', stripped):
                add(re.sub(r'^\s*(\d+[\.\)\:])\s+', '', stripped))
            elif _ROMAN_QUESTION_PATTERN.match(stripped):
                add(_ROMAN_QUESTION_PATTERN.sub('', stripped))
            elif '?' in stripped and len(stripped) < 500:
                add(stripped)

        if not entries:
            # Fall back to sentence-style question marks in running text.
            for match in re.compile(r'([A-Z][^\?]+\?)', re.DOTALL).finditer(text):
                candidate = match.group(1).strip()
                if len(candidate) > 20:
                    add(candidate)

        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for entry in entries:
            if entry['text'] not in seen:
                seen.add(entry['text'])
                unique.append(entry)
        return unique

    def extract_questions_from_text(self, text: str) -> list[str]:
        return [e['text'] for e in self.extract_questions_with_meta(text)]

    def analyze_document(self, file_path: str, filename: str | None = None) -> dict[str, Any]:
        """Extract questions from one paper.

        The returned dict always carries ``ok``. A file that cannot be read or
        is an unsupported type reports ``ok=False`` with an ``error``, which is
        what lets the caller distinguish "this paper failed" from "this paper
        was read fine but contained no questions".
        """
        ext = None
        if filename and '.' in filename:
            ext = '.' + filename.split('.')[-1].lower()
        if not ext:
            ext = PurePosixPath(file_path).suffix.lower()

        name = filename or file_path

        # Check the *extension*, not the whole path.
        if not supports_extension(ext):
            return {
                'ok': False,
                'error': f'Unsupported file type: {ext or "unknown"}',
                'questions': [],
                'filename': name,
            }

        try:
            doc = extract_document(file_path, file_type=ext)
        except Exception as exc:
            return {
                'ok': False,
                'error': str(exc),
                'questions': [],
                'filename': name,
            }

        year = self.extract_paper_year(doc.text, filename)

        detailed = self.extract_questions_with_meta(doc.text, year=year)
        return {
            'ok': True,
            'questions': [e['text'] for e in detailed],
            'question_meta': detailed,
            'filename': name,
            'year': year,
            'extracted_text_length': len(doc.text),
        }

    def find_similar_questions(
        self, questions: list[str], threshold: float = 0.8
    ) -> list[tuple[int, int, float]]:
        """Return (i, j, score) pairs of semantically equivalent questions.

        Uses the knowledge base's own embedding backend (the same vectors that
        back retrieval) rather than comparing strings or building a second
        embedder.
        """
        if not questions or self.knowledge_base is None:
            return []
        embed = getattr(self.knowledge_base, 'embed', None)
        if not callable(embed):
            return []
        try:
            embeddings = embed(questions)
        except Exception:
            return []
        if not embeddings or len(embeddings) != len(questions):
            return []

        import numpy as np

        matrix = np.asarray(embeddings, dtype=float)
        norms = np.linalg.norm(matrix, axis=1)
        usable = norms > 0
        if not usable.any():
            return []
        normalized = np.zeros_like(matrix)
        normalized[usable] = matrix[usable] / norms[usable][:, None]
        similarity = normalized @ normalized.T

        pairs: list[tuple[int, int, float]] = []
        for i in range(len(questions)):
            for j in range(i + 1, len(questions)):
                if not usable[i] or not usable[j]:
                    continue
                score = float(similarity[i, j])
                if score >= threshold:
                    pairs.append((i, j, score))
        return pairs

    def rank_questions(self, questions: list[dict], num_questions: int = 10) -> list[dict]:
        """Rank questions by repetition and stated marks, then take top N.

        Frequency dominates because a question that keeps appearing is the best
        predictor of what will be asked again; stated marks break ties toward
        the questions that cost the most time in the exam.
        """
        for i, q in enumerate(questions):
            q['id'] = i + 1
            freq = q.get('frequency', 1) or 0
            marks = q.get('marks')
            try:
                marks_value = float(marks) if marks is not None else 0.0
            except (TypeError, ValueError):
                marks_value = 0.0
            imp = q.get('importance', 'Medium')
            score = freq * 10 + min(marks_value, 20) / 2
            if imp == 'High':
                score += 5
            q['score'] = score
        sorted_questions = sorted(
            questions, key=lambda x: x.get('score', 0), reverse=True
        )
        return sorted_questions[:num_questions]
