"""Deterministic query-understanding layer for the RAG chat pipeline.

Phase 1 of the agent architecture: ``analyze_query`` turns a raw student
message into a :class:`QueryIntent` describing what the user wants and a
conservatively corrected query string meant to improve retrieval.

Design constraints
------------------
* RAG remains the only source of study knowledge. This module never adds
  knowledge; it only classifies the *shape* of the request and repairs
  obvious cue-word typos so downstream retrieval is more likely to find the
  relevant material.
* Corrections are intentionally conservative. Only a small, curated set of
  seed typo expansions plus a guarded vocabulary-aware hook (a single
  insertion/deletion onto a small intent vocabulary) are ever applied.
  Unknown or ambiguous queries keep their original wording.
* No external API, corpus, dictionary, or learned model is used. A better
  vocabulary-aware mechanism can be swapped into
  :func:`_vocabulary_correct_word` later without changing any caller.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Intent taxonomy
# ---------------------------------------------------------------------------
INTENT_GENERAL = "general"
INTENT_EXPLANATION = "explanation"
INTENT_SUMMARY = "summary"
INTENT_COMPARISON = "comparison"
INTENT_ANALYSIS = "analysis"
INTENT_SIMPLE = "simple"
INTENT_DETAILED = "detailed"
INTENT_EXAM = "exam"
INTENT_BULLETS = "bullets"
INTENT_DEFINITION = "definition"

# ---------------------------------------------------------------------------
# Requested formats
# ---------------------------------------------------------------------------
FORMAT_GENERAL = "general"
FORMAT_EXPLANATION = "explanation"
FORMAT_SUMMARY = "summary"
FORMAT_COMPARISON = "comparison"
FORMAT_ANALYSIS = "analysis"
FORMAT_SIMPLE = "simple explanation"
FORMAT_DETAILED = "detailed explanation"
FORMAT_BULLET_POINTS = "bullet points"
FORMAT_DEFINITION = "definition"
FORMAT_EXAM = "exam answer"
FORMAT_EXAM_2_MARK = "2-mark answer"
FORMAT_EXAM_5_MARK = "5-mark answer"
FORMAT_EXAM_10_MARK = "10-mark answer"

# Intents that are mutually exclusive document tasks. When two or more of
# these appear together the query is treated as ambiguous.
_TASK_INTENTS = frozenset({INTENT_COMPARISON, INTENT_ANALYSIS, INTENT_SUMMARY})

# Priority used to pick a primary task in an ambiguous query (highest first).
_TASK_PRIORITY = (INTENT_COMPARISON, INTENT_ANALYSIS, INTENT_SUMMARY)

# Minimum overall confidence for the analysis (intent + correction) to be
# trusted. Below this value callers must fall back to the original query and
# the general grounded prompt.
RELIABLE_CONFIDENCE_THRESHOLD = 0.6

# ---------------------------------------------------------------------------
# Conservative typo corrections
# ---------------------------------------------------------------------------
# Small, curated set of common misspellings / informal abbreviations for the
# cue words that matter for understanding and retrieval. This is deliberately
# tiny: explicit seed entries are high-confidence, everything else is handled
# by the guarded vocabulary hook below.
_SEED_TYPOS: dict[str, str] = {
    # explanation cues
    "explaim": "explain",
    "expain": "explain",
    "explein": "explain",
    "explian": "explain",
    "expln": "explain",
    "expla": "explain",
    # analysis cues
    "analysses": "analyze",
    "analize": "analyze",
    "analsys": "analysis",
    "anlaysis": "analysis",
    # comparison cues
    "comapre": "compare",
    "compair": "compare",
    "compaire": "compare",
    "comare": "compare",
    # simple-format cues
    "simpe": "simple",
    "simpel": "simple",
    # summary cues
    "sumary": "summary",
    "summarry": "summary",
    "sumerize": "summarize",
    "sumbarry": "summary",
    # exam marks cues
    "mrks": "marks",
    "mrk": "mark",
    "markes": "marks",
    # definition cues
    "difinition": "definition",
    "defintion": "definition",
    "deffinition": "definition",
    "definiion": "definition",
    # detail / bullet cues
    "detaled": "detailed",
    "detaild": "detailed",
    "bulletes": "bullets",
    "bulletpoints": "bullet points",
    # informal shorthand commonly typed by students
    "u": "you",
    "ur": "your",
    "plz": "please",
    "pls": "please",
    "thx": "thanks",
    "ans": "answer",
}

# Vocabulary the guarded hook may correct a token *to*. Only words here can
# ever appear as a correction target, so generic corrections can never reach
# beyond the intent vocabulary.
_INTENT_VOCAB: frozenset[str] = frozenset(
    {
        "explain",
        "explanation",
        "summary",
        "summarize",
        "summarise",
        "compare",
        "comparison",
        "analysis",
        "analyze",
        "analyse",
        "simple",
        "detailed",
        "detail",
        "exam",
        "marks",
        "mark",
        "bullet",
        "bullets",
        "points",
        "definition",
        "define",
        "difference",
        "meaning",
        "overview",
        "versus",
        "describe",
    }
)

# ---------------------------------------------------------------------------
# Intent cue patterns (matched against lower-cased, whitespace-normalized text)
# ---------------------------------------------------------------------------
_CUE_COMPARISON = re.compile(
    r"\b(compare|comparison|versus|vs\.?|difference between|"
    r"differ from|contrast|contrasting|similarities and differences)\b"
)
_CUE_ANALYSIS = re.compile(r"\banaly[sz](?:e|es|ed|ing|is)\b")
_CUE_SUMMARY = re.compile(
    r"\b(summary|summariz(?:e|ed|ing)|summaris(?:e|ed|ing)|tldr|overview|synopsis)\b"
)
_CUE_EXPLANATION = re.compile(
    r"\b(explain(?:s|ed|ing)?|explanation|describe(?:s|d|ing)?|"
    r"how does|how do|how is|why does|why do|why is|what causes)\b"
)
_CUE_DEFINITION = re.compile(
    r"\b(define(?:s|d)?|definition|what is|what are|what's|"
    r"what is meant by|meaning of)\b"
)
_CUE_SIMPLE = re.compile(
    r"\bin simple (words|terms|language|english)\b|"
    r"\bsimple (words|language)\b|"
    r"\bsimply put\b|"
    r"\bexplain like i'?m\b|"
    r"\beli5\b|"
    r"\bin easy (words|language)\b|"
    r"\bsimplif(?:y|ied|ying)\b"
)
_CUE_DETAILED = re.compile(
    r"\bin detail\b|\bdetailed\b|\belaborate\b|\bthorough(?:ly)?\b|"
    r"\bcomprehensive\b|\bstep by step\b|\bin depth\b|deep dive"
)
_CUE_BULLETS = re.compile(
    r"\bbullet ?points?\b|\bbullets?\b|\bpoint wise\b|\bpointwise\b|"
    r"\bin points\b|\bkey points\b|\bas a list\b|\blist format\b|"
    r"\bin bullet format\b"
)
_CUE_EXAM_WORD = re.compile(
    r"\b(exams?|examinations?|board exam|final exam|"
    r"marks? answer|exam question|exam answer)\b"
)
_CUE_EXAM_MARKS = re.compile(r"\b(\d{1,2})\s*-?\s*marks?\b")

# A query is flagged ``is_visual`` when the student is asking about (or wants
# to be shown) a figure, diagram, chart, image, or similar visual inside the
# material. Visual retrieval is only ever activated for such queries.
_VISUAL_NOUN = (
    r"diagram|figure|fig\.?|flowchart|flow ?chart|architecture(?:al)?|"
    r"chart|graph|image|picture|schematic|illustration|visuals?|"
    r"screenshot|screen ?shot"
)
_CUE_VISUAL = re.compile(
    r"\b(?:" + _VISUAL_NOUN + r")\b"
    r"|\bshow me\b|\bcan you show\b|"
    r"\bwhich (?:diagram|figure|image|picture|chart)\b|"
    r"\bshould (?:i|we) draw\b|"
    r"\bdraw (?:a|an|the) (?:diagram|figure|flowchart|flow chart|chart)\b"
)

_WORD = re.compile(r"(\W*)([\w]*)(\W*)")


@dataclass(frozen=True)
class QueryIntent:
    """Structured description of what a query asks for.

    Attributes
    ----------
    intent_type:
        One of the ``INTENT_*`` constants. ``"general"`` means no specific
        intent signal was found.
    corrected_query:
        The conservative, retrieval-oriented rewrite of the query. Preserves
        the caller's original wording whenever the analysis is not reliable.
    requested_format:
        One of the ``FORMAT_*`` constants describing how the answer should be
        presented (e.g. ``"10-mark answer"``, ``"simple explanation"``).
    confidence:
        ``0.0`` for empty input, above the reliability threshold only when the
        intent classification is unambiguous and any correction is safe.
    original_query:
        The caller's raw message, kept verbatim for provenance.
    is_visual:
        True when the query asks about material visuals (figures, diagrams,
        charts, images). Callers should then also retrieve visual evidence -
        never for regular text questions.
    """

    intent_type: str
    corrected_query: str
    requested_format: str
    confidence: float
    original_query: str = ""
    is_visual: bool = False


def is_reliable(intent: QueryIntent) -> bool:
    """True when ``intent`` should be acted upon by the answer pipeline."""
    return intent.confidence >= RELIABLE_CONFIDENCE_THRESHOLD


def _correct_token(token: str) -> str:
    """Apply one conservative correction to a whitespace-delimited token."""
    match = _WORD.fullmatch(token)
    if not match or not match.group(2):
        return token
    prefix, word, suffix = match.group(1), match.group(2), match.group(3)
    return prefix + _correct_word(word) + suffix


def _correct_word(word: str) -> str:
    lower = word.lower()
    if not lower:
        return word
    if lower in _SEED_TYPOS:
        fixed = _SEED_TYPOS[lower]
        return fixed.capitalize() if word[:1].isupper() else fixed
    replacement = _vocabulary_correct_word(lower)
    if replacement is None:
        return word
    return replacement.capitalize() if word[:1].isupper() else replacement


def _vocabulary_correct_word(word: str) -> str | None:
    """Conservative vocabulary-aware correction (no substitutions).

    A token is only rewritten when it differs from exactly one vocabulary
    word by a single *insertion or deletion*. Substitutions are never applied
    generically because they can silently turn one real word into another
    (e.g. ``analyte`` -> ``analyze``). This is the extension point where a
    better dictionary/embedding-aware mechanism can be plugged in later.
    """
    if len(word) < 5 or word in _INTENT_VOCAB:
        return None
    candidates = [
        candidate
        for candidate in _INTENT_VOCAB
        if candidate != word and _one_insert_or_delete(word, candidate)
    ]
    if len(candidates) == 1:
        return candidates[0]
    return None


def _one_insert_or_delete(a: str, b: str) -> bool:
    """True when ``a`` differs from ``b`` by exactly one char insertion/deletion."""
    if len(b) == len(a) + 1:
        return any(b[:i] + b[i + 1 :] == a for i in range(len(b)))
    if len(a) == len(b) + 1:
        return any(a[:i] + a[i + 1 :] == b for i in range(len(a)))
    return False


def _explicit_format(exam_number: int | None, matched: frozenset[str]) -> str:
    if exam_number is not None:
        return {
            2: FORMAT_EXAM_2_MARK,
            5: FORMAT_EXAM_5_MARK,
            10: FORMAT_EXAM_10_MARK,
        }.get(exam_number, FORMAT_EXAM)
    if INTENT_EXAM in matched:
        return FORMAT_EXAM
    if INTENT_SIMPLE in matched:
        return FORMAT_SIMPLE
    if INTENT_DETAILED in matched:
        return FORMAT_DETAILED
    if INTENT_BULLETS in matched:
        return FORMAT_BULLET_POINTS
    if INTENT_COMPARISON in matched:
        return FORMAT_COMPARISON
    if INTENT_ANALYSIS in matched:
        return FORMAT_ANALYSIS
    if INTENT_SUMMARY in matched:
        return FORMAT_SUMMARY
    if INTENT_DEFINITION in matched:
        return FORMAT_DEFINITION
    if INTENT_EXPLANATION in matched:
        return FORMAT_EXPLANATION
    return FORMAT_GENERAL


def _detect_intents(text: str) -> tuple[frozenset[str], int | None]:
    """Return (matched intent types, exam mark count if requested)."""
    lowered = text.lower()
    matched: set[str] = set()
    if _CUE_COMPARISON.search(lowered):
        matched.add(INTENT_COMPARISON)
    if _CUE_ANALYSIS.search(lowered):
        matched.add(INTENT_ANALYSIS)
    if _CUE_SUMMARY.search(lowered):
        matched.add(INTENT_SUMMARY)
    if _CUE_EXPLANATION.search(lowered):
        matched.add(INTENT_EXPLANATION)
    if _CUE_DEFINITION.search(lowered):
        matched.add(INTENT_DEFINITION)
    if _CUE_SIMPLE.search(lowered):
        matched.add(INTENT_SIMPLE)
    if _CUE_DETAILED.search(lowered):
        matched.add(INTENT_DETAILED)
    if _CUE_BULLETS.search(lowered):
        matched.add(INTENT_BULLETS)
    if _CUE_EXAM_WORD.search(lowered):
        matched.add(INTENT_EXAM)
    exam_number: int | None = None
    marks_match = _CUE_EXAM_MARKS.search(lowered)
    if marks_match is not None:
        exam_number = int(marks_match.group(1))
        matched.add(INTENT_EXAM)
    return frozenset(matched), exam_number


def analyze_query(raw_query: str) -> QueryIntent:
    """Analyze a raw query into a :class:`QueryIntent`.

    The returned ``corrected_query``:

    * improves retrieval by fixing only obvious cue-word typos;
    * preserves the original wording whenever the analysis is ambiguous or
      low-confidence, so the user's actual intent is never rewritten;
    * never touches unknown content words (no dictionary is used), so a
      misspelled topic keeps its spelling unless it is a curated seed.
    """
    text = " ".join(raw_query.split())
    if not text:
        return QueryIntent(
            intent_type=INTENT_GENERAL,
            corrected_query=raw_query,
            requested_format=FORMAT_GENERAL,
            confidence=0.0,
            original_query=raw_query,
        )

    corrected_text = " ".join(_correct_token(token) for token in text.split())
    matched, exam_number = _detect_intents(corrected_text)
    is_visual = _CUE_VISUAL.search(corrected_text.lower()) is not None

    tasks = matched & _TASK_INTENTS
    requested_format = _explicit_format(exam_number, matched)

    if INTENT_EXAM in matched:
        intent_type = INTENT_EXAM
        confidence = 0.9
    elif len(tasks) >= 2:
        intent_type = next(
            task for task in _TASK_PRIORITY if task in tasks
        )
        confidence = 0.4
    elif len(tasks) == 1:
        intent_type = next(iter(tasks))
        confidence = 0.9
    elif INTENT_SIMPLE in matched:
        intent_type = INTENT_SIMPLE
        confidence = 0.9
    elif INTENT_DETAILED in matched:
        intent_type = INTENT_DETAILED
        confidence = 0.9
    elif INTENT_BULLETS in matched:
        intent_type = INTENT_BULLETS
        confidence = 0.9
    elif INTENT_DEFINITION in matched:
        intent_type = INTENT_DEFINITION
        confidence = 0.9
    elif INTENT_EXPLANATION in matched:
        intent_type = INTENT_EXPLANATION
        confidence = 0.9
    else:
        intent_type = INTENT_GENERAL
        confidence = 0.3

    if confidence >= RELIABLE_CONFIDENCE_THRESHOLD:
        corrected_query = corrected_text
    else:
        corrected_query = raw_query

    return QueryIntent(
        intent_type=intent_type,
        corrected_query=corrected_query,
        requested_format=requested_format,
        confidence=confidence,
        original_query=raw_query,
        is_visual=is_visual,
    )