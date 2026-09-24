"""Unit tests for stripping model reasoning/thinking output before display."""

from __future__ import annotations

from rag.llm.cleanup import (
    RESPONSE_CLOSE_TAG,
    RESPONSE_OPEN_TAG,
    THINKING_CLOSE_TAG,
    THINKING_OPEN_TAG,
    strip_thinking_sections,
)


def _thinking_block(bodies: list[str]) -> str:
    return (
        f"{THINKING_OPEN_TAG}\n"
        + "\n".join(bodies)
        + f"\n{THINKING_CLOSE_TAG}"
    )


class TestStripThinkingSections:
    def test_strips_full_qwen_style_thinking_block(self) -> None:
        raw = (
            _thinking_block(
                [
                    "The user asked about photosynthesis.",
                    "I recall the light-dependent reactions happen in thylakoids.",
                ]
            )
            + f"\n\n{RESPONSE_OPEN_TAG}\n"
            "Plants use sunlight, water, and CO2 to produce glucose.\n"
            f"{RESPONSE_CLOSE_TAG}"
        )

        assert (
            strip_thinking_sections(raw)
            == "Plants use sunlight, water, and CO2 to produce glucose."
        )

    def test_removes_thinking_but_keeps_plain_answer_after(self) -> None:
        raw = (
            _thinking_block(["internal reasoning goes here"])
            + "\nThe answer is glucose and oxygen."
        )

        assert strip_thinking_sections(raw) == "The answer is glucose and oxygen."

    def test_handles_response_when_thinking_block_omitted(self) -> None:
        raw = f"{RESPONSE_OPEN_TAG}\nNewton's second law: F = ma.\n{RESPONSE_CLOSE_TAG}"

        assert strip_thinking_sections(raw) == "Newton's second law: F = ma."

    def test_truncated_response_tag_keeps_answer_after_it(self) -> None:
        raw = (
            f"{THINKING_OPEN_TAG}\n"
            "reasoning\n"
            f"{RESPONSE_OPEN_TAG}\n"
            "The answer is brief."
        )

        assert strip_thinking_sections(raw) == "The answer is brief."

    def test_handles_unclosed_thinking_followed_by_response(self) -> None:
        raw = (
            f"{THINKING_OPEN_TAG}\n"
            "reasoning without a close tag\n"
            f"{RESPONSE_OPEN_TAG}\n"
            "The answer is complete.\n"
            f"{RESPONSE_CLOSE_TAG}"
        )

        assert strip_thinking_sections(raw) == "The answer is complete."

    def test_normal_answer_without_tags_is_unchanged(self) -> None:
        answer = (
            "Photosynthesis converts light energy into chemical energy. "
            "The Calvin cycle fixes CO2 into glucose."
        )

        assert strip_thinking_sections(answer) == answer

    def test_legitimate_answer_content_is_preserved(self) -> None:
        answer = (
            "Comparison operators like < and > compare values; "
            "XML tags look like <tag>value</tag>."
        )
        raw = (
            _thinking_block(["reasoning"])
            + f"\n{RESPONSE_OPEN_TAG}\n{answer}\n{RESPONSE_CLOSE_TAG}"
        )

        assert strip_thinking_sections(raw) == answer

    def test_line_containing_thinking_word_in_prose_is_not_a_tag(self) -> None:
        answer = "The student should avoid careless thinking when writing essays."
        assert strip_thinking_sections(answer) == answer

    def test_reasoning_only_output_collapses_to_empty(self) -> None:
        raw = f"{THINKING_OPEN_TAG}\nall reasoning and nothing else"

        assert strip_thinking_sections(raw) == ""

    def test_indented_tags_are_still_removed(self) -> None:
        raw = (
            f"  {THINKING_OPEN_TAG}  \n"
            "reasoning\n"
            f"   {THINKING_CLOSE_TAG}   \n"
            "Answer."
        )

        assert strip_thinking_sections(raw) == "Answer."

    def test_empty_and_whitespace_input(self) -> None:
        assert strip_thinking_sections("") == ""
        assert strip_thinking_sections("   \n \n  ") == ""


class TestRealWorldQwenFormat:
    """Regression tests for the exact standalone-``response`` format that a real
    qwen3:4b website validation reproduced: unmarked reasoning prose followed
    by a bare  response  marker line, with the answer coming afterwards."""

    def test_removes_unmarked_reasoning_before_standalone_response(self) -> None:
        raw = (
            "Let me analyze the retrieved study material to determine the "
            "main topic discussed in this document.\n\n"
            "The document appears to focus on budgeting, forecasting, and "
            "financial reporting. Looking at the headings, most sections "
            "deal with how organizations plan, allocate, and review their "
            "financial resources, which strongly suggests the subject is "
            "financial management.\n\n"
            "Let me formulate a concise answer that directly addresses the "
            "question without adding any information outside the retrieved "
            "material.\n\n"
            "The answer should be a direct statement about the main topic, "
            "followed by a brief explanation that's concise and based only "
            "on the retrieved material.\n\n"
            "response\n\n"
            "The main topic discussed in this document is financial "
            "management concepts..."
        )

        expected = (
            "The main topic discussed in this document is financial "
            "management concepts..."
        )
        result = strip_thinking_sections(raw)
        assert result == expected
        assert "Let me analyze" not in result
        assert "Let me formulate" not in result

    def test_whitespace_variations_of_standalone_response_marker(self) -> None:
        assert (
            strip_thinking_sections("internal reasoning\nresponse\nThe answer is X.")
            == "The answer is X."
        )
        assert (
            strip_thinking_sections("internal reasoning\nresponse  \nThe answer is Y.")
            == "The answer is Y."
        )
        assert (
            strip_thinking_sections("internal reasoning\n  response\n\nThe answer is Z.")
            == "The answer is Z."
        )

    def test_response_without_opening_thinking_returns_only_after_marker(self) -> None:
        result = strip_thinking_sections(
            "some unmarked reasoning prose\nresponse\nThe answer is X."
        )
        assert result == "The answer is X."

    def test_reasoning_then_response_with_no_answer_returns_empty(self) -> None:
        assert strip_thinking_sections("internal reasoning\nresponse") == ""
        assert strip_thinking_sections("internal reasoning\n  response  \n") == ""

    def test_normal_answer_without_marker_is_unchanged(self) -> None:
        answer = "The answer is X."
        assert strip_thinking_sections(answer) == answer

    def test_legitimate_angle_brackets_are_never_touched(self) -> None:
        answer = "Use <table> tags in HTML."
        assert strip_thinking_sections(answer) == answer

    def test_response_word_inside_sentence_is_not_a_delimiter(self) -> None:
        answer = "The primary immune response is faster than the initial one."
        assert strip_thinking_sections(answer) == answer

    def test_response_marker_content_after_is_preserved_exactly(self) -> None:
        answer = (
            "The main topic is financial management concepts. "
            "Key terms include <budget>, <forecast>, and <report>. "
            "See [Source 1]."
        )
        raw = f"unmarked reasoning\nresponse\n\n{answer}\n"
        assert strip_thinking_sections(raw) == answer

    def test_real_format_is_idempotent(self) -> None:
        raw = (
            "unmarked reasoning prose about the question\n"
            "more deliberation\n"
            "response\n\n"
            "The answer is grounded in the retrieved material."
        )
        once = strip_thinking_sections(raw)
        twice = strip_thinking_sections(once)
        assert once == "The answer is grounded in the retrieved material."
        assert twice == once

    def test_full_wrapper_still_strips_real_marker(self) -> None:
        result = strip_thinking_sections(
            "unmarked reasoning\n"
            f"{RESPONSE_OPEN_TAG}\n"
            "The answer is X.\n"
            f"{RESPONSE_CLOSE_TAG}"
        )
        assert result == "The answer is X."