"""Reusable, deterministic text chunking for RAG preprocessing.

The chunker accepts normalized text and returns an ordered list of non-empty
chunks. It prefers to split between paragraphs and, inside a paragraph that is
too long, between sentences. Each returned chunk respects ``chunk_size``
(character budget) and carries a configurable overlap: the tail of a chunk is
carried into the start of the next one so context survives chunk boundaries.

``split_ranges`` also reports each chunk's start ``offset`` inside the source
text, which lets the pipeline attach page/slide information to every chunk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_JOINER = "\n\n"
_WORD_JOINER = " "


@dataclass(frozen=True)
class ChunkRange:
    """A chunk together with its character offset inside the source text."""

    text: str
    offset: int


@dataclass(frozen=True)
class TextChunker:
    """Split text into size-bounded chunks with optional overlap."""

    chunk_size: int = 1500
    overlap: int = 150

    def __post_init__(self) -> None:
        if self.chunk_size < 1:
            raise ValueError("chunk_size must be >= 1")
        if self.overlap < 0:
            raise ValueError("overlap must be >= 0")
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

    def split(self, text: str) -> list[str]:
        """Return chunked text as an ordered list of non-empty strings."""
        return [rng.text for rng in self.split_ranges(text)]

    def split_ranges(self, text: str) -> list[ChunkRange]:
        """Return chunked text with each chunk's start offset in ``text``."""
        text = text.strip()
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [ChunkRange(text=text, offset=0)]

        units, separators = self._expand_units(text)
        if not units:
            return []

        base_ranges = self._assemble(units, separators)
        return self._apply_overlap(base_ranges)

    def _expand_units(self, text: str) -> tuple[list[str], list[str]]:
        """Split ``text`` into atomic units plus the separator before each.

        Units inside one paragraph join with a single space; units from
        different paragraphs join with a blank line.
        """
        units: list[str] = []
        separators: list[str] = []

        for paragraph in self._paragraphs(text):
            if units:
                separators.append(_JOINER)
            for index, unit in enumerate(self._unitize(paragraph)):
                if index > 0:
                    separators.append(_WORD_JOINER)
                units.append(unit)
        return units, separators

    def _paragraphs(self, text: str) -> list[str]:
        return [
            paragraph.strip()
            for paragraph in _PARAGRAPH_SPLIT.split(text)
            if paragraph.strip()
        ]

    def _unitize(self, paragraph: str) -> list[str]:
        """Break one paragraph into atomic units no longer than chunk_size."""
        if len(paragraph) <= self.chunk_size:
            return [paragraph]

        units: list[str] = []
        buffer = ""
        for sentence in _SENTENCE_SPLIT.split(paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) > self.chunk_size:
                if buffer:
                    units.append(buffer)
                    buffer = ""
                units.extend(self._character_units(sentence))
            elif not buffer:
                buffer = sentence
            elif len(buffer) + len(_WORD_JOINER) + len(sentence) <= self.chunk_size:
                buffer += _WORD_JOINER + sentence
            else:
                units.append(buffer)
                buffer = sentence
        if buffer:
            units.append(buffer)
        return units

    def _character_units(self, text: str) -> list[str]:
        return [
            text[start : start + self.chunk_size]
            for start in range(0, len(text), self.chunk_size)
        ]

    def _assemble(self, units: list[str], separators: list[str]) -> list[ChunkRange]:
        chunks: list[ChunkRange] = []
        buffer = ""
        base_offset = cursor = 0

        for index, unit in enumerate(units):
            separator = separators[index - 1] if index else ""
            if not buffer:
                buffer = unit
                base_offset = cursor
                cursor += len(unit)
                continue

            joined = buffer + separator + unit
            if len(joined) <= self.chunk_size:
                buffer = joined
                cursor += len(separator) + len(unit)
            else:
                chunks.append(ChunkRange(text=buffer, offset=base_offset))
                buffer = unit
                base_offset = cursor
                cursor += len(unit)

        if buffer:
            chunks.append(ChunkRange(text=buffer, offset=base_offset))
        return chunks

    def _apply_overlap(self, base_ranges: list[ChunkRange]) -> list[ChunkRange]:
        result = [base_ranges[0]]
        for index in range(1, len(base_ranges)):
            tail = self._overlap_tail(result[index - 1].text)
            current = base_ranges[index]
            if not tail:
                result.append(current)
                continue
            combined = tail + _JOINER + current.text
            if len(combined) > self.chunk_size:
                headroom = self.chunk_size - len(current.text) - len(_JOINER)
                if headroom > 0:
                    tail = tail[:headroom]
                    combined = tail + _JOINER + current.text
                else:
                    combined = current.text
            result.append(ChunkRange(text=combined, offset=current.offset))
        return result

    def _overlap_tail(self, text: str) -> str:
        """The last ``overlap`` characters, aligned to a sentence boundary."""
        if self.overlap == 0 or not text:
            return ""
        tail = text[-self.overlap :]
        boundary = self._last_boundary(tail)
        return tail[boundary:] if boundary >= 0 else tail

    @staticmethod
    def _last_boundary(tail: str) -> int:
        """Index just after the last sentence/paragraph boundary in ``tail``."""
        boundary = -1
        for marker in (". ", "! ", "? ", "\n\n", "\n"):
            index = tail.rfind(marker)
            if index >= 0:
                boundary = max(boundary, index + len(marker))
        return boundary