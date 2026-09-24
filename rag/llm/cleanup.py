"""Defensive cleanup of model output before it reaches students.

Some thinking-capable models (e.g. Qwen3 behind Ollama) can emit an internal
reasoning trace even when ``think`` is disabled. Ollama surfaces that trace
wrapped in well-known whole-line delimiter tags::

    thinking
    <model's internal reasoning...>
    /thinking

    response
    <final student answer...>
    /response

In practice Qwen3 also emits a reduced form where the opening ``thinking`` tag
is missing entirely: a block of unreferenced reasoning prose is followed by a
standalone ``response`` line, after which the real answer starts::

    <internal reasoning text ...>
    response
    <final student answer...>

:func:`strip_thinking_sections` removes only this known structure using
whole-line, exact tag matches. It drops everything before the first standalone
``response`` marker line, so hidden reasoning never reaches the student even
when no ``thinking`` opener was present. Genuine study content that happens to
contain ordinary angle brackets (``<``, ``>``) or the words "thinking"/
"response" inside a sentence is never touched, and answers that have no
reasoning structure pass through unchanged.
"""

from __future__ import annotations

import re

THINKING_OPEN_TAG = "thinking"
THINKING_CLOSE_TAG = "/thinking"
RESPONSE_OPEN_TAG = "response"
RESPONSE_CLOSE_TAG = "/response"

_TAG_RE = re.compile(r"^\s*(thinking|/thinking|response|/response)\s*$")


def _tag_name(line: str) -> str | None:
    """Return the known tag name for *line*, or ``None`` if it is not one."""
    if not _TAG_RE.match(line):
        return None
    return line.strip().lower()


def strip_thinking_sections(text: str) -> str:
    """Strip Qwen-style reasoning output and unwrap the answer wrapper.

    The returned text never contains the model's internal thinking trace. A
    truncated response that contains *only* reasoning collapses to ``""`` so
    callers can fall back.

    Normal answers without reasoning structure are returned unchanged.
    """
    if not text:
        return text

    lines = text.splitlines()
    tags = {i: tag for i, tag in enumerate(map(_tag_name, lines)) if tag}

    remove: set[int] = set()

    # Pass 1 -- drop  thinking ... /thinking  reasoning blocks.
    i = 0
    while i < len(lines):
        if tags.get(i) != THINKING_OPEN_TAG:
            i += 1
            continue

        close_idx = next(
            (j for j in range(i + 1, len(lines))
             if tags.get(j) == THINKING_CLOSE_TAG),
            None,
        )
        if close_idx is not None:
            remove.update(range(i, close_idx + 1))
            i = close_idx + 1
            continue

        # Unterminated opening: reasoning runs up to a later  response  tag.
        response_idx = next(
            (j for j in range(i + 1, len(lines))
             if tags.get(j) == RESPONSE_OPEN_TAG),
            None,
        )
        if response_idx is not None:
            remove.update(range(i, response_idx))
            i = response_idx
            continue

        # Reasoning with no answer at all (truncated output): drop it only
        # when it starts the whole response; otherwise leave it untouched.
        if i == 0:
            remove.update(range(0, len(lines)))
            break
        i += 1

    kept = [line for index, line in enumerate(lines) if index not in remove]

    # Pass 2 -- the first standalone  response  line marks the boundary
    # between reasoning (everything before it) and the real answer. Qwen3
    # emits this marker even without a  thinking  opening tag, so the marker
    # is searched for anywhere in the text, not only at the start.
    marker_idx = next(
        (index for index, line in enumerate(kept)
         if _tag_name(line) == RESPONSE_OPEN_TAG),
        None,
    )
    if marker_idx is None:
        return "\n".join(kept).strip()

    body = kept[marker_idx + 1:]
    close_idx = next(
        (j for j, line in enumerate(body)
         if _tag_name(line) == RESPONSE_CLOSE_TAG),
        None,
    )
    if close_idx is not None:
        body = body[:close_idx]
    return "\n".join(body).strip()