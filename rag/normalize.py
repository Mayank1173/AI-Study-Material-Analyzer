"""Text normalization applied to every extracted document.

Normalization is deterministic and idempotent so the pipeline can be retried
without changing chunk output. It produces a single consistent representation:
LF line endings, no leading/trailing whitespace on any line, paragraphs
separated by exactly one blank line, and no stray control characters.
"""

from __future__ import annotations

import re

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalize_text(text: str) -> str:
    """Normalize raw document text into a stable, chunkable representation."""
    if text is None:
        return ""

    text = str(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS.sub("", text)

    lines = [line.strip() for line in text.split("\n")]
    normalized: list[str] = []
    blank_pending = False
    for line in lines:
        if line:
            if blank_pending and normalized:
                normalized.append("")
            blank_pending = False
            normalized.append(line)
        elif normalized:
            blank_pending = True

    return "\n".join(normalized).strip()


def is_empty(text: str) -> bool:
    """Return True when the text contains no meaningful content."""
    return not normalize_text(text)