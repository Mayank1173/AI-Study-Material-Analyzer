"""Multi-source evidence collection for the RAG chat pipeline.

Phase 2 of the agent architecture. Retrieval remains the sole knowledge
source; this layer only decides *which* retrieved chunks are handed to the
grounded prompt. It:

1. pulls a slightly larger candidate pool than the final context size. The
   SQLite store already scores every chunk of the filtered owner's set, so
   reading a few more candidates has no measurable retrieval cost;
2. deduplicates near-identical chunks *within a single material* (overlapping
   chunk windows). Chunks from *different* materials stay distinct even when
   their text is identical - each material is a legitimate, separately
   citable source;
3. bounds how many chunks one material may contribute, so a document dense in
   similar chunks cannot crowd out every other relevant material. Selection is
   made strictly in score order, so relevance stays the primary ranking
   factor: diversity never pulls content from outside the relevance-ranked
   candidate pool and never drops the globally top-scoring chunk;
4. groups the final evidence by material so the context builder can present
   ``SOURCE A`` / ``SOURCE B`` blocks while ``[Source N]`` numbers stay
   aligned with the public source references.

All existing ownership/course/material scoping is preserved because this
layer only calls :meth:`KnowledgeBase.search` with the same filters the
answer pipeline uses today.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rag.models import ChunkMetadata, SearchResult, VisualElement

if TYPE_CHECKING:
    from rag.knowledge_base import KnowledgeBase

# How many top-ranked chunks to score for an answer turn. The store already
# scores every chunk of the owner's set, so this is a cheap upper bound that
# gives the diversity step enough relevant candidates to balance across
# materials without dumping the whole database into the prompt.
EVIDENCE_CANDIDATE_POOL = 8

# Maximum number of chunks one material may contribute to a single answer.
# With the default context size (``DEFAULT_ANSWER_TOP_K = 3``) this cap never binds for a single-material answer; it only limits one material's
# *share* of a larger multi-source prompt, which is exactly when source
# diversity matters.
MAX_CHUNKS_PER_MATERIAL = 3

# How many visual elements may be attached to a visual answer. Visual evidence
# is supplementary to text chunks, so it stays small.
DEFAULT_VISUAL_EVIDENCE = 2

_WHITESPACE = re.compile(r"\s+")


def canonical_text(text: str) -> str:
    """Normalize text for near-identical duplication checks."""
    return _WHITESPACE.sub(" ", text.strip().lower())


def deduplicate_results(results: list[SearchResult]) -> list[SearchResult]:
    """Keep the first (highest-scoring) occurrence of a chunk text per material.

    Duplicates are only detected within a single ``material_id`` so two
    *different* materials that happen to share the same text remain distinct
    evidence sources, each representable as its own ``SOURCE`` block.
    """
    seen: set[tuple[str | None, str]] = set()
    deduped: list[SearchResult] = []
    for result in results:
        key = (result.material_id, canonical_text(result.text))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped


def diversify_by_material(
    results: list[SearchResult],
    *,
    per_material_cap: int = MAX_CHUNKS_PER_MATERIAL,
) -> list[SearchResult]:
    """Bound how many chunks a single material may contribute.

    ``results`` must already be ranked by relevance (score descending), which
    is how the vector store returns them. Iterating in that order and skipping
    a chunk only once its material has reached the cap guarantees:

    - the globally top-scoring chunk is always kept (relevance is primary);
    - diversity can never *add* content that was not already a top-ranked
      candidate for this query;
    - a material can never claim more than its fair share of an answer.
    """
    if per_material_cap < 1:
        raise ValueError("per_material_cap must be >= 1")
    counts: dict[str, int] = {}
    diversified: list[SearchResult] = []
    for result in results:
        count = counts.get(result.material_id, 0)
        if count >= per_material_cap:
            continue
        counts[result.material_id] = count + 1
        diversified.append(result)
    return diversified


def group_by_material(results: list[SearchResult]) -> list[SearchResult]:
    """Regroup results into material groups, preserving first-appearance order.

    Within a material the original (relevance) order is kept. This lets the
    context builder emit ``SOURCE A`` / ``SOURCE B`` blocks while the
    ``[Source N]`` numbering stays consistent with ``sources_from_results``.
    """
    groups: dict[str, list[SearchResult]] = {}
    order: list[str] = []
    for result in results:
        target = groups.setdefault(result.material_id, [])
        if not target:
            order.append(result.material_id)
        target.append(result)
    grouped: list[SearchResult] = []
    for material_id in order:
        grouped.extend(groups[material_id])
    return grouped


def collect_evidence(
    knowledge_base: KnowledgeBase,
    *,
    query: str,
    user_id: str,
    course_id: str | None = None,
    material_id: str | None = None,
    max_evidence: int = 3,
    candidate_pool: int = EVIDENCE_CANDIDATE_POOL,
    per_material_cap: int = MAX_CHUNKS_PER_MATERIAL,
) -> list[SearchResult]:
    """Collect, deduplicate, diversify, and group evidence for one query.

    Retrieval itself is left entirely to ``knowledge_base.search``; this
    function never inspects another user's chunks and never weakens the
    existing user/course/material scoping passed through unchanged.

    Returns
    -------
    list[SearchResult]
        At most ``max_evidence`` chunks, grouped by material, in relevance
        order within each group. Empty when nothing relevant was found (the
        caller then keeps the existing no-context behaviour).
    """
    if max_evidence < 1:
        return []
    if not query or not query.strip():
        return []
    pool_size = max(candidate_pool, max_evidence)
    candidates = knowledge_base.search(
        query,
        user_id=user_id,
        course_id=course_id,
        material_id=material_id,
        top_k=pool_size,
    )
    selected = diversify_by_material(
        deduplicate_results(candidates),
        per_material_cap=per_material_cap,
    )[:max_evidence]
    return group_by_material(selected)


def collect_visual_evidence(
    knowledge_base: KnowledgeBase,
    *,
    query: str,
    user_id: str,
    course_id: str | None = None,
    material_id: str | None = None,
    max_visuals: int = DEFAULT_VISUAL_EVIDENCE,
) -> list[VisualElement]:
    """Collect visual elements relevant to a visual query.

    This is a strict companion to :func:`collect_evidence` and is only called
    when ``QueryIntent.is_visual`` is true. It uses the knowledge base's
    ``visual_search`` (keyword scoped, same ownership rules as text search) and
    is best-effort: a store without visual support, or any unexpected failure,
    simply yields no visual evidence instead of failing the answer turn.

    Returns
    -------
    list[VisualElement]
        At most ``max_visuals`` visuals matching the query. Empty when the
        store cannot provide visuals or none match.
    """
    if max_visuals < 1:
        return []
    if not query or not query.strip():
        return []
    search = getattr(knowledge_base, "visual_search", None)
    if not callable(search):
        return []
    try:
        return search(
            query,
            user_id=user_id,
            course_id=course_id,
            material_id=material_id,
            top_k=max_visuals,
        )
    except Exception:
        return []


_KEYWORD_KINDS: tuple[tuple[str, str], ...] = (
    ("question bank", "Question bank"),
    ("previous year", "Previous-year paper"),
    ("previous-year", "Previous-year paper"),
    ("pyq", "Previous-year paper"),
    ("pyqs", "Previous-year paper"),
    ("module", "Module"),
    ("presentation", "Presentation"),
    ("slide", "Presentation"),
    ("ppt", "Presentation"),
    ("notes", "Notes"),
    ("note", "Notes"),
    ("summary", "Summary"),
)


def source_kind(metadata: ChunkMetadata) -> str:
    """Derive a human-readable source kind from chunk metadata.

    The backend's ``material_type`` is never passed into the RAG layer, so
    source kind has to be inferred from the original filename plus the
    ``source_type`` file extension. This is purely descriptive: it never
    encodes an authority ranking and is never used to filter or re-rank
    evidence.
    """
    filename = (metadata.original_filename or "").strip().lower()
    stem = filename.rsplit(".", 1)[0] if filename else ""
    for needle, kind in _KEYWORD_KINDS:
        if needle in filename or (stem and needle in stem):
            return kind
    ext = (metadata.source_type or "").strip().lower()
    by_extension = {
        ".pdf": "PDF document",
        ".pptx": "Presentation",
        ".ppt": "Presentation",
        ".docx": "Word document",
        ".doc": "Word document",
        ".txt": "Text file",
        ".md": "Markdown file",
        ".csv": "Spreadsheet",
        ".xlsx": "Spreadsheet",
        ".xls": "Spreadsheet",
    }
    return by_extension.get(ext, "Study material")