"""Shared, best-effort helpers for detecting visual content in documents.

The extractors only record *metadata* about visual elements: where they are,
their type, and the caption/nearby text already visible in the document. They
never decode pixels, so a visual's ``description`` is always empty and
``pixel_analyzed`` is always ``False``. Everything here is intentionally
fallible - each helper returns conservative defaults instead of raising, so
visual detection can never break document text extraction.
"""

from __future__ import annotations

import re

from rag.models import (
    VISUAL_TYPE_ARCHITECTURE,
    VISUAL_TYPE_CHART,
    VISUAL_TYPE_DIAGRAM,
    VISUAL_TYPE_FIGURE,
    VISUAL_TYPE_FLOWCHART,
    VISUAL_TYPE_IMAGE,
    VISUAL_TYPE_TABLE,
    VISUAL_TYPE_UNKNOWN,
)

#: Words/short phrases that mark a sentence as an image/figure caption.
_CAPTION_PATTERN = re.compile(
    r"\b(figure|fig\.?|diagram|chart|graph|illustration|screenshot|image|picture)\b",
    re.IGNORECASE,
)

#: Map from caption keywords to the canonical visual-type label. "Figure" /
#: "Fig." are checked before "chart"/"graph" so a caption like "Figure 9:
#: Throughput graph" is classified as a figure, matching how documents label
#: their visuals. The most specific structural labels (flowchart,
#: architecture, diagram) still win when present.
_TYPE_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("flowchart", VISUAL_TYPE_FLOWCHART),
    ("flow chart", VISUAL_TYPE_FLOWCHART),
    ("architecture", VISUAL_TYPE_ARCHITECTURE),
    ("diagram", VISUAL_TYPE_DIAGRAM),
    ("figure", VISUAL_TYPE_FIGURE),
    ("fig.", VISUAL_TYPE_FIGURE),
    ("illustration", VISUAL_TYPE_FIGURE),
    ("table", VISUAL_TYPE_TABLE),
    ("chart", VISUAL_TYPE_CHART),
    ("graph", VISUAL_TYPE_CHART),
    ("plot", VISUAL_TYPE_CHART),
    ("screenshot", VISUAL_TYPE_IMAGE),
    ("image", VISUAL_TYPE_IMAGE),
    ("picture", VISUAL_TYPE_IMAGE),
)


def find_caption(text: str, default: str = "") -> str:
    """Return the first line (then first sentence) that reads like a caption.

    Captions usually live on their own line in the raw document, so lines are
    tried before punctuation-based sentence splits (which can tear apart a
    caption like ``Fig. 2 shows...`` or ``Figure 1: ...``). Returns ``default``
    when no candidate exists.
    """
    if not text:
        return (default or "").strip()
    for line in text.splitlines():
        line = line.strip()
        if line and _CAPTION_PATTERN.search(line):
            return line
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        sentence = sentence.strip()
        if sentence and _CAPTION_PATTERN.search(sentence):
            return sentence
    return (default or "").strip()


def guess_visual_type(text: str, fallback: str = VISUAL_TYPE_UNKNOWN) -> str:
    """Guess a canonical visual type from caption/canvas text.

    Keyword rules are ordered so the most specific labels (flowchart,
    architecture) win over generic ones (diagram, figure). When nothing
    matches, ``fallback`` is returned unchanged.
    """
    low = (text or "").lower()
    for keyword, visual_type in _TYPE_KEYWORDS:
        if keyword in low:
            return visual_type
    return fallback