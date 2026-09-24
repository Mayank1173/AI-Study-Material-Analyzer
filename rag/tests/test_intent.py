"""Tests for the deterministic query-understanding layer (rag.intent)."""

from __future__ import annotations

from rag.intent import (
    FORMAT_BULLET_POINTS,
    FORMAT_DEFINITION,
    FORMAT_EXAM,
    FORMAT_EXAM_2_MARK,
    FORMAT_EXAM_5_MARK,
    FORMAT_EXAM_10_MARK,
    FORMAT_SIMPLE,
    INTENT_ANALYSIS,
    INTENT_BULLETS,
    INTENT_COMPARISON,
    INTENT_DEFINITION,
    INTENT_DETAILED,
    INTENT_EXAM,
    INTENT_EXPLANATION,
    INTENT_GENERAL,
    INTENT_SIMPLE,
    INTENT_SUMMARY,
    RELIABLE_CONFIDENCE_THRESHOLD,
    QueryIntent,
    analyze_query,
    is_reliable,
)


class TestSpecExamples:
    def test_explaim_deadlock(self) -> None:
        intent = analyze_query("explaim deadlock")
        assert isinstance(intent, QueryIntent)
        assert intent.intent_type == INTENT_EXPLANATION
        assert intent.corrected_query == "explain deadlock"
        assert intent.confidence >= RELIABLE_CONFIDENCE_THRESHOLD

    def test_analysses_tcp(self) -> None:
        intent = analyze_query("analysses tcp")
        assert intent.intent_type == INTENT_ANALYSIS
        assert intent.corrected_query == "analyze tcp"

    def test_comapre_tcp_udp(self) -> None:
        intent = analyze_query("comapre tcp udp")
        assert intent.intent_type == INTENT_COMPARISON
        assert intent.corrected_query == "compare tcp udp"

    def test_explain_in_simpe_words(self) -> None:
        intent = analyze_query("explain in simpe words")
        assert intent.intent_type == INTENT_SIMPLE
        assert intent.requested_format == FORMAT_SIMPLE
        assert intent.requested_format == "simple explanation"
        assert intent.corrected_query == "explain in simple words"

    def test_give_10_marks_answer(self) -> None:
        intent = analyze_query("give 10 mrks ans for deadlock")
        assert intent.intent_type == INTENT_EXAM
        assert intent.requested_format == FORMAT_EXAM_10_MARK
        assert intent.requested_format == "10-mark answer"
        assert "mrks" not in intent.corrected_query
        assert "marks" in intent.corrected_query


class TestCorrectlySpelledQueries:
    def test_plain_explanation_preserves_wording(self) -> None:
        raw = "Explain deadlock briefly"
        intent = analyze_query(raw)
        assert intent.intent_type == INTENT_EXPLANATION
        assert intent.corrected_query == raw

    def test_comparison(self) -> None:
        intent = analyze_query("Compare TCP and UDP")
        assert intent.intent_type == INTENT_COMPARISON
        assert intent.requested_format == "comparison"

    def test_summary(self) -> None:
        intent = analyze_query("Summarize the operating system notes")
        assert intent.intent_type == INTENT_SUMMARY

    def test_analysis(self) -> None:
        intent = analyze_query("Analyze the TCP handshake")
        assert intent.intent_type == INTENT_ANALYSIS

    def test_definition(self) -> None:
        intent = analyze_query("What is photosynthesis?")
        assert intent.intent_type == INTENT_DEFINITION
        assert intent.requested_format == FORMAT_DEFINITION

    def test_bullet_points(self) -> None:
        intent = analyze_query("write bullet points about tcp")
        assert intent.intent_type == INTENT_BULLETS
        assert intent.requested_format == FORMAT_BULLET_POINTS

    def test_detailed(self) -> None:
        intent = analyze_query("explain in detail")
        assert intent.intent_type == INTENT_DETAILED
        assert intent.requested_format == "detailed explanation"

    def test_exam_mark_sizes(self) -> None:
        two = analyze_query("give 2 marks answer for deadlock")
        assert two.intent_type == INTENT_EXAM
        assert two.requested_format == FORMAT_EXAM_2_MARK
        assert two.requested_format == "2-mark answer"

        five = analyze_query("give a 5-mark answer for deadlock")
        assert five.intent_type == INTENT_EXAM
        assert five.requested_format == FORMAT_EXAM_5_MARK
        assert five.requested_format == "5-mark answer"

        ten = analyze_query("give 10 marks answer for deadlock")
        assert ten.intent_type == INTENT_EXAM
        assert ten.requested_format == FORMAT_EXAM_10_MARK
        assert ten.requested_format == "10-mark answer"

        bare = analyze_query("give an exam answer for deadlock")
        assert bare.intent_type == INTENT_EXAM
        assert bare.requested_format == FORMAT_EXAM


class TestEmptyAndWhitespace:
    def test_empty_query(self) -> None:
        intent = analyze_query("")
        assert intent.intent_type == INTENT_GENERAL
        assert intent.confidence == 0.0
        assert intent.corrected_query == ""
        assert is_reliable(intent) is False

    def test_whitespace_only_query(self) -> None:
        intent = analyze_query("   ")
        assert intent.confidence == 0.0
        assert intent.corrected_query == "   "


class TestAmbiguousAndLowConfidence:
    def test_conflicting_tasks_are_ambiguous(self) -> None:
        raw = "summarize and compare the notes"
        intent = analyze_query(raw)
        assert intent.confidence < RELIABLE_CONFIDENCE_THRESHOLD
        assert intent.corrected_query == raw

    def test_low_confidence_bare_topic(self) -> None:
        intent = analyze_query("deadlock")
        assert intent.intent_type == INTENT_GENERAL
        assert intent.confidence < RELIABLE_CONFIDENCE_THRESHOLD
        assert intent.corrected_query == "deadlock"

    def test_unrecognizable_words_preserved(self) -> None:
        raw = "zzqx zzw"
        intent = analyze_query(raw)
        assert intent.confidence < RELIABLE_CONFIDENCE_THRESHOLD
        assert intent.corrected_query == raw


class TestConservativeCorrection:
    def test_content_word_typos_are_not_rewritten(self) -> None:
        intent = analyze_query("explaim deadlok")
        assert intent.corrected_query == "explain deadlok"

    def test_vocabulary_hook_fixes_single_missing_letter(self) -> None:
        intent = analyze_query("sumarize the notes")
        assert intent.corrected_query == "summarize the notes"
        assert intent.intent_type == INTENT_SUMMARY
        assert intent.confidence >= RELIABLE_CONFIDENCE_THRESHOLD

    def test_no_generic_substitution_of_real_words(self) -> None:
        intent = analyze_query("analyte formation")
        assert "analyte" in intent.corrected_query

    def test_seed_correction_preserves_capitalization(self) -> None:
        assert analyze_query("Explaim tcp").corrected_query == "Explain tcp"

    def test_punctuation_is_preserved_around_correction(self) -> None:
        intent = analyze_query("explaim deadlock,")
        assert intent.corrected_query == "explain deadlock,"


class TestQueryIntentContract:
    def test_original_query_is_recorded(self) -> None:
        intent = analyze_query("explaim deadlock")
        assert intent.original_query == "explaim deadlock"

    def test_is_reliable_matches_threshold(self) -> None:
        assert is_reliable(analyze_query("explaim deadlock")) is True
        assert is_reliable(analyze_query("deadlock")) is False
        assert RELIABLE_CONFIDENCE_THRESHOLD == 0.6