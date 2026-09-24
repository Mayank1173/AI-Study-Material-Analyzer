"""Conversation context and follow-up reference resolution (Phase 3).

Conversation history is used ONLY to understand references in a follow-up
("it", "this", "that", "the second one", "the above", "make that a 10-mark
answer", ...) so it can be rewritten into a standalone retrieval query.

Hard rules
----------
* RAG remains the only source of factual/study knowledge. This module never
  adds knowledge; it only binds anaphoric references to a topic that already
  exists in the user's own previous message.
* Previous AI answers are never used as evidence, never merged into the
  retrieval query, and never passed to the context builder. They are kept in
  the conversation record only so future features can reuse them, and the
  answer pipeline is responsible for never treating them as RAG context.
* Resolution is deterministic and conservative. When a reference cannot be
  bound to a confident topic the original query is preserved instead of
  inventing a topic.
* History is bounded (``ConversationStore`` keeps only the most recent N
  turns), so a conversation never grows without limit.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Bounded-conversation limits
# ---------------------------------------------------------------------------
MAX_HISTORY_TURNS = 8

# Minimum resolution confidence for the pipeline to trust a rewrite. Values
# below this mean "no confident reference was found - keep the original".
RESOLUTION_CONFIDENCE_THRESHOLD = 0.6

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConversationTurn:
    """One user/assistant exchange, kept only for reference resolution.

    ``user_message`` is the raw message as typed; ``resolved_query`` is the
    standalone query that Phase 1 actually saw (topic extraction prefers it
    because it carries the real subject a later follow-up will refer to).
    ``assistant_answer`` is stored for completeness/ordering only - it is
    never fed back into retrieval or the grounded prompt.
    """

    user_message: str
    resolved_query: str = ""
    assistant_answer: str = ""
    timestamp: float = 0.0


@dataclass(eq=False)
class Conversation:
    """A bounded series of turns owned by exactly one user."""

    conversation_id: str
    user_id: str
    turns: list[ConversationTurn] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def history(self, *, limit: int | None = None) -> list[ConversationTurn]:
        """Return the most recent turns (defaults to all stored turns)."""
        if limit is None:
            return list(self.turns)
        return list(self.turns[-limit:])


@dataclass(frozen=True)
class Resolution:
    """Outcome of rewriting a follow-up into a standalone query.

    ``was_resolved`` is True only when a reference cue was matched and bound
    to a confident topic. Low-confidence cases keep ``resolved_query`` equal
    to the original input and ``was_resolved`` False.
    """

    resolved_query: str
    confidence: float
    was_resolved: bool
    matched_rule: str | None = None


class ConversationStore:
    """Process-local, in-memory conversation store with ownership scoping.

    This is deliberately NOT a database redesign: state lives in memory and is
    keyed by ``conversation_id``. Every retrieval enforces the owning user, so
    a user can never read another user's conversation history.
    """

    def __init__(self, max_turns: int = MAX_HISTORY_TURNS) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._max_turns = max_turns

    def ensure(self, conversation_id: str, *, user_id: str) -> Conversation:
        """Return the user-owned conversation, creating a fresh one if needed.

        If ``conversation_id`` already exists but belongs to a different user,
        a brand-new conversation owned by ``user_id`` replaces it. The foreign
        history is discarded and is never returned to the new owner.
        """
        existing = self._conversations.get(conversation_id)
        if existing is not None and existing.user_id == user_id:
            return existing
        conversation = Conversation(
            conversation_id=conversation_id, user_id=user_id
        )
        self._conversations[conversation_id] = conversation
        return conversation

    def get(
        self, conversation_id: str, *, user_id: str
    ) -> Conversation | None:
        """Return the conversation only when ``user_id`` owns it."""
        conversation = self._conversations.get(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            return None
        return conversation

    def record_turn(
        self,
        conversation_id: str,
        *,
        user_id: str,
        user_message: str,
        resolved_query: str,
        assistant_answer: str,
        timestamp: float | None = None,
    ) -> bool:
        """Append one turn and trim history to the bounded window.

        Returns False when the conversation is not owned by ``user_id``.
        """
        conversation = self.get(conversation_id, user_id=user_id)
        if conversation is None:
            return False
        conversation.turns.append(
            ConversationTurn(
                user_message=user_message,
                resolved_query=resolved_query or user_message,
                assistant_answer=assistant_answer,
                timestamp=timestamp or time.time(),
            )
        )
        if len(conversation.turns) > self._max_turns:
            del conversation.turns[: len(conversation.turns) - self._max_turns]
        return True

    def clear(self) -> None:
        """Drop every conversation (used to reset between tests)."""
        self._conversations.clear()


def make_conversation_id() -> str:
    """Generate a conversation id for clients that do not supply one."""
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Reference resolution
# ---------------------------------------------------------------------------

# Ordinal words used by "the first one / the second one / ..." references.
_ORDINALS = {
    "first": 1,
    "1st": 1,
    "second": 2,
    "2nd": 2,
    "third": 3,
    "3rd": 3,
    "fourth": 4,
    "4th": 4,
    "fifth": 5,
    "5th": 5,
    "sixth": 6,
    "6th": 6,
    "seventh": 7,
    "7th": 7,
    "eighth": 8,
    "8th": 8,
    "ninth": 9,
    "9th": 9,
    "tenth": 10,
    "10th": 10,
}

_PRONOUNS = frozenset({"it", "its", "this", "that", "these", "those", "them"})

# Guards for "that": when it directly follows one of these it is almost always
# a conjunction/relative marker, not a reference to the previous turn.
_THAT_GUARD = frozenset(
    {"so", "such", "given", "provided", "assuming", "suppose", "consider"}
)

# Small set of function words / intent cues that never carry a topic. Used to
# decide whether a query names its own subject (then it is treated as
# standalone) or merely refers back to the previous turn.
_GENERIC_WORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "of", "for", "to", "with", "on", "at",
        "in", "from", "about", "by", "as", "via", "is", "are", "was", "were",
        "be", "been", "being", "do", "does", "did", "done", "it", "its", "it's",
        "this", "that", "these", "those", "them", "they", "their", "there",
        "what", "why", "how", "when", "where", "which", "who", "whom", "whose",
        "me", "my", "mine", "i", "i'm", "you", "your", "we", "our", "us",
        "please", "can", "could", "would", "will", "may", "might", "shall",
        "should", "explain", "explaination", "explanation", "describe",
        "define", "definition", "tell", "give", "give me", "compare",
        "comparison", "contrast", "summarize", "summarise", "summary",
        "simplify", "simple", "simpler", "detailed", "detail", "elaborate",
        "make", "made", "making", "answer", "answers", "mark", "marks",
        "point", "points", "one", "two", "more", "again", "say", "said",
        "want", "know", "learn", "understand", "need", "like", "example",
        "examples", "etc", "me", "my", "everything", "nothing",
        "above", "below", "hi", "hey", "hello", "yo", "howdy", "greetings",
        "thanks", "thank", "thx", "cheers", "there",
    }
)

# Leading cue patterns stripped (in order) when extracting a topic. Each entry
# is a simple anchored alternation, kept small so the whole set is easy to
# audit. Clean typo variants of the intent verbs are included because
# resolution runs BEFORE Phase 1's typo correction.
_LEADING_CUES: tuple[re.Pattern, ...] = (
    re.compile(
        r"^(?:hi|hey|hello|yo|howdy|greetings|thanks|thank\s+you|thx|cheers)\b"
        r"\s*(?:there)?\s*[,.!]*",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:please|could\s+(?:you|i|we)|can\s+(?:you|i|we)|"
        r"would\s+you\s+mind|would\s+you|may\s+i|"
        r"does\s+anyone\s+know|help\s+me\s+(?:understand|with))\s+",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:i\s+would\s+like\s+to|i\s+(?:want|need)\s+to|i'?d\s+like\s+to)"
        r"\s+(?:know|learn|understand)?\s*(?:about|regarding)?\s+",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:explain|explaim|expain|explein|explian|expln|expla|describe|define|"
        r"summari[sz]e|discuss|clarify|cover)\w*\s+"
        r"(?:(?:to\s+me|about|on|regarding)\s+)?"
        r"(?:the\s+(?:concept|idea|notion|working|details?)\s+of\s+)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:elaborate\s+(?:on|about)|detail\s+(?:me\s+)?(?:on|about)|"
        r"walk\s+me\s+through|break\s+down|compare|contrast)\s+",
        re.IGNORECASE,
    ),
    re.compile(r"^tell\s+me\s+(?:about|regarding|the|what|more\s+about)\s+", re.IGNORECASE),
    re.compile(
        r"^give\s+me\s+(?:an?\s+)?(?:overview|explanation|summary|details?|introduction)"
        r"(?:\s+(?:of|about|on))?\s+",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:what's|what\s+(?:is|are|do|does|about)|"
        r"how\s+(?:is|are|does|do|did|can)|why\s+(?:is|are|does|do|did)|"
        r"when\s+do|where\s+does)\s+",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:(?:the\s+)?(?:main|key|major)?\s*difference\s+between)\s+",
        re.IGNORECASE,
    ),
    re.compile(r"^i\s+don'?t\s+understand\s+", re.IGNORECASE),
)

# Trailing modifier phrases that do not belong in a topic string.
_TRAILING_MOD = re.compile(
    r"\s+(?:again|more|please)\s*$|"
    r"\s+in\s+(?:simple|simpler|easy|easier)\s+(?:words?|terms|language|english)\s*$|"
    r"\s+in\s+(?:more\s+)?detail\s*$|"
    r"\s+for\s+(?:the\s+)?exam(?:s)?\s*$|"
    r"\s+(?:as|as\s+a)\s+an?\s*\d{1,2}(?:\s*/\s*\d{1,2})?\s*-?\s*marks?\s+answer\s*$|"
    r"\s+with\s+examples?\s*$|"
    r"\s+step\s+by\s+step\s*$|"
    r"\s+in\s+bullet(?:\s+points?|points?)?\s*$",
    re.IGNORECASE,
)

# Separators used to enumerate distinct items inside a previous message.
_ITEM_SEP = re.compile(
    r"[.!?]+|\s*[;,]\s+|\s+and\s+|\s+as\s+well\s+as\s+|\s+vs\.?\s+|"
    r"\s+versus\s+|\s+&\s+"
)

_ORDINAL_RE = re.compile(
    r"\b(?:the\s+)?"
    r"(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
    r"1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th)"
    r"\s+(?:one|point|condition|rule|concept|method|example|item|part)\b",
    re.IGNORECASE,
)

_WORD = re.compile(r"[A-Za-z]{2,}")

_EXAM_MARK_RE = re.compile(
    r"\b(?:make\s+)?(?:that|it|this)\s+(?:into\s+)?(?:an?\s+)?"
    r"\d{1,2}(?:\s*/\s*\d{1,2})?\s*-?\s*marks?\s+answer\b",
    re.IGNORECASE,
)

_EXAM_MARK_AS_RE = re.compile(
    r"\b(?:as|as\s+a)\s+an?\s*\d{1,2}(?:\s*/\s*\d{1,2})?\s*-?\s*marks?\s+answer\b",
    re.IGNORECASE,
)

_SIMPLER_RE = re.compile(
    r"\b(?:make|put)\s+(?:it|this|that)\s+simpler\b|"
    r"\bsimplif(?:y|ies|ied|ying)\s+(?:it|this|that)\b|"
    r"\b(?:in|into)\s+simpler\s+(?:words?|terms|language|english)\b|"
    r"\b(?:in|into)\s+(?:simple|easier)\s+(?:words?|terms|language|english)\b|"
    r"\bexplain\s+like\s+i'?m\s+\d\b",
    re.IGNORECASE,
)

_DETAILED_RE = re.compile(
    r"\belaborate\b|"
    r"\b(?:explain|expand|talk|go|tell\s+me)\s+(?:further|deeper|more)\b|"
    r"\b(?:in|into)\s+more\s+detail\b|"
    r"\bmove\s+deeper\b|\bgo\s+into\s+detail\b|\btell\s+me\s+more\b",
    re.IGNORECASE,
)

_RECAP_RE = re.compile(
    r"\b(?:again|repeat|once\s+more|re[- ]explain|re[- ]do|revise)\b",
    re.IGNORECASE,
)

_ABOVE_RE = re.compile(r"\bthe\s+above\b", re.IGNORECASE)

_COM_LHS = re.compile(
    r"\b(?:comapre|compair|comare|compaire|compare|comparison|contrast)\s+"
    r"(it|its|this|that|these|those|them)\s+"
    r"(?:with|and|to|vs\.?|versus)\b",
    re.IGNORECASE,
)

_COM_RHS = re.compile(
    r"\b(?:comapre|compair|comare|compaire|compare|comparison\s+of|contrast)"
    r"\s+.*?\s+(?:with|and|to|vs\.?|versus)\s+"
    r"(it|its|this|that|these|those|them)\b",
    re.IGNORECASE,
)

_DIFF_LHS = re.compile(
    r"\bdifference\s+between\s+(it|its|this|that|these|those|them)\s+and\b",
    re.IGNORECASE,
)

_DIFF_RHS = re.compile(
    r"\bdifference\s+between\s+.*?\s+and\s+(it|its|this|that|these|those|them)\b",
    re.IGNORECASE,
)

_PRONOUN_RE = re.compile(
    r"\b(it|its|this|that|these|those|them)\b", re.IGNORECASE
)

_PURE_REFERENCE = frozenset(
    {
        "it", "its", "this", "that", "these", "those", "them", "the above",
        "above", "the last one", "previous", "the previous",
    }
)


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _has_substantive(text: str) -> bool:
    return any(word not in _GENERIC_WORDS for word in _words(text))


def _possessive(topic: str) -> str:
    if topic.endswith("'s"):
        return topic
    if topic.endswith("s"):
        return topic + "'"
    return topic + "'s"


def _strip_leading(text: str) -> str:
    previous = None
    while previous != text:
        previous = text
        for cue in _LEADING_CUES:
            candidate = cue.sub("", text, count=1)
            if candidate != text:
                text = candidate
                break
    return text


def _strip_trailing(text: str) -> str:
    previous = None
    while previous != text:
        previous = text
        text = _TRAILING_MOD.sub("", text)
    return text


def _clean_segment(part: str) -> str:
    cleaned = " ".join(part.split())
    cleaned = cleaned.strip(" .,;:!?()\"'")
    cleaned = _strip_leading(cleaned)
    cleaned = _strip_trailing(cleaned)
    cleaned = " ".join(cleaned.split()).strip(" .,;:!?()\"'")
    return cleaned


def split_items(text: str) -> list[str]:
    """Enumerate the distinct topics/items a message covers.

    Used to turn "the second one" into the actual second item. Splitting is
    deliberately conservative: sentence boundaries, trailing punctuation, and
    explicit list connectors only.
    """
    segments: list[str] = []
    for part in _ITEM_SEP.split(text):
        cleaned = _clean_segment(part)
        if cleaned and cleaned.lower() not in _PURE_REFERENCE:
            segments.append(cleaned)
    return segments


def extract_topic(user_message: str) -> str | None:
    """Extract the primary topic a user's message is about.

    Returns None when no usable topic can be recovered (an empty message, a
    message that only contains references, or a message with no content
    words). Callers must preserve the original query in those cases.
    """
    text = " ".join(user_message.split())
    if not text:
        return None
    stripped = _strip_trailing(_strip_leading(text))
    segments = split_items(stripped) if stripped else []
    if not segments:
        return None
    primary = segments[0]
    if primary.lower() in _PURE_REFERENCE or not _has_substantive(primary):
        return None
    return primary


def _replace_span(text: str, start: int, end: int, replacement: str) -> str:
    return text[:start] + replacement + text[end:]


def _drop_span(text: str, span: tuple[int, int]) -> str:
    return text[: span[0]] + " " + text[span[1] :]


def _bind_phrase(phrase: str, topic: str) -> str:
    """Replace reference pronouns inside ``phrase`` with the bound topic."""

    def _sub(match: re.Match) -> str:
        token = match.group(0)
        return _possessive(topic) if token.lower() == "its" else topic

    return _PRONOUN_RE.sub(_sub, phrase)


def _bind_item(item: str, topic: str | None) -> str:
    """Bind an ordinal item to the previous topic when needed."""
    stripped = item.strip()
    lowered = stripped.lower()
    if topic and lowered.startswith("its "):
        return _possessive(topic) + stripped[len("its") :]
    if topic and lowered.startswith("it "):
        return topic + stripped[len("it") :]
    without_the = re.sub(r"^the\s+", "", stripped, flags=re.IGNORECASE)
    if _has_substantive(without_the):
        return without_the
    return topic or without_the


def _apply_exam_mark(text: str, topic: str) -> Resolution | None:
    marker = _EXAM_MARK_RE.search(text)
    if marker is not None and not _has_substantive(
        _drop_span(text, marker.span())
    ):
        phrase = marker.group(0)
        bound = _bind_phrase(phrase, topic)
        if bound != phrase:
            return Resolution(
                _replace_span(text, *marker.span(), bound),
                0.95,
                True,
                "exam-mark",
            )
        return Resolution(f"{topic} {text}".strip(), 0.95, True, "exam-mark")
    marker_as = _EXAM_MARK_AS_RE.search(text)
    if marker_as is not None and not _has_substantive(
        _drop_span(text, marker_as.span())
    ):
        return Resolution(f"{topic} {text}".strip(), 0.95, True, "exam-mark")
    return None


def _apply_implicit_modifier(text: str, topic: str) -> Resolution | None:
    """Handle format-only modifiers that implicitly target the previous turn.

    These rewrite the request into canonical phrasing so Phase 1 can detect
    the format intent (e.g. "in simple words" -> INTENT_SIMPLE, "N mark
    answer" -> INTENT_EXAM) while keeping the previous topic for retrieval.
    """
    exam = _apply_exam_mark(text, topic)
    if exam is not None:
        return exam

    simpler = _SIMPLER_RE.search(text)
    if simpler is not None and not _has_substantive(
        _drop_span(text, simpler.span())
    ):
        return Resolution(f"explain {topic} in simple words", 0.95, True, "simplify")

    detailed = _DETAILED_RE.search(text)
    if detailed is not None and not _has_substantive(
        _drop_span(text, detailed.span())
    ):
        return Resolution(f"explain {topic} in detail", 0.95, True, "elaborate")

    recap = _RECAP_RE.search(text)
    if recap is not None and len(_words(text)) <= 4 and not _has_substantive(
        _drop_span(text, recap.span())
    ):
        return Resolution(f"explain {topic} again", 0.85, True, "again")

    above = _ABOVE_RE.search(text)
    if above is not None:
        return Resolution(
            _replace_span(text, *above.span(), topic), 0.95, True, "above"
        )
    return None


def _apply_comparison(text: str, topic: str) -> Resolution | None:
    """Bind a pronoun that is one side of a comparison/difference phrase."""
    for pattern in (_COM_LHS, _DIFF_LHS):
        match = pattern.search(text)
        if match is None:
            continue
        start = match.start()
        pronoun = _PRONOUN_RE.search(match.group(0))
        if pronoun is None:
            continue
        idx = start + pronoun.start()
        end = idx + len(pronoun.group(0))
        replacement = _possessive(topic) if pronoun.group(0).lower() == "its" else topic
        return Resolution(
            _replace_span(text, idx, end, replacement), 0.95, True, "comparison"
        )
    for pattern in (_COM_RHS, _DIFF_RHS):
        match = pattern.search(text)
        if match is None:
            continue
        # The pronoun is the last word group of the match.
        pronoun = _PRONOUN_RE.search(match.group(0))
        if pronoun is None:
            continue
        span_start = match.start() + pronoun.start()
        span_end = span_start + len(pronoun.group(0))
        replacement = _possessive(topic) if pronoun.group(0).lower() == "its" else topic
        return Resolution(
            _replace_span(text, span_start, span_end, replacement),
            0.95,
            True,
            "comparison",
        )
    return None


def _apply_pronouns(text: str, topic: str | None) -> Resolution | None:
    """Replace referential pronouns with the bound topic, when confident.

    A pronoun is only treated as a cross-turn reference when the text before
    it does not already name a substantive subject. Standalone queries that
    happen to include "its"/"this" (e.g. "Photosynthesis and its role in
    plants") are left untouched.
    """
    if not topic:
        return None
    original = text
    matches = list(_PRONOUN_RE.finditer(text))
    resolved: str | None = None
    for match in reversed(matches):
        token = match.group(0)
        lower = token.lower()
        start = match.start()
        end = match.end()
        if len(token) >= 3 and token.isupper():
            continue  # likely an acronym, never a reference
        if lower == "that":
            before = text[:start]
            words_before = _words(before)
            if words_before and words_before[-1] in _THAT_GUARD:
                continue
        before_text = text[:start]
        if _has_substantive(_strip_leading(before_text)):
            continue  # query names its own subject
        budg = end
        while budg < len(text) and (text[budg] == "'" or text[budg].isalpha()):
            budg += 1
        if text[end : end + 1] == "'":
            replacement = _possessive(topic)  # "it's role" -> "TCP's role"
            end = budg
        else:
            replacement = _possessive(topic) if lower == "its" else topic
        resolved = _replace_span(text, start, end, replacement)
        text = resolved
    if resolved is None or resolved == original:
        return None
    return Resolution(resolved, 0.95, True, "pronoun")


def resolve_query(
    raw_query: str, history: list[ConversationTurn]
) -> Resolution:
    """Resolve a follow-up into a standalone retrieval query.

    The query is rewritten ONLY when it contains an explicit reference cue and
    the previous turn provides a confident topic. Standalone queries and
    low-confidence references are preserved unchanged.
    """
    text = " ".join(raw_query.split())
    if not text:
        return Resolution(text, 0.0, False)
    if not history:
        return Resolution(text, 0.0, False)

    turn = history[-1]
    effective = turn.resolved_query or turn.user_message
    topic = extract_topic(effective) or extract_topic(turn.user_message)

    ordinal = _ORDINAL_RE.search(text)
    if ordinal is not None:
        items = split_items(effective)
        number = _ORDINALS.get(ordinal.group(1).lower(), 0)
        item = items[number - 1] if 0 < number <= len(items) else None
        if item is None:
            item = topic
        if item:
            bound = _bind_item(item, topic)
            return Resolution(
                _replace_span(text, *ordinal.span(), bound),
                0.95,
                True,
                "ordinal",
            )
        return Resolution(text, 0.0, False)

    if topic:
        modifier = _apply_implicit_modifier(text, topic)
        if modifier is not None:
            return modifier
        comparison = _apply_comparison(text, topic)
        if comparison is not None:
            return comparison
        pronouns = _apply_pronouns(text, topic)
        if pronouns is not None:
            return pronouns

    return Resolution(text, 0.0, False)