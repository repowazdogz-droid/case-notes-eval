"""Deterministic behaviour of the recording checker.

The checker is the grader. If it is not exactly reproducible and does not do what
the rubric says, the whole study is unsound. These tests pin the load-bearing
behaviours: it flags an interpretation stated as fact, it does NOT flag the same
label inside quoted speech or behind an observational qualifier, and it is
byte-for-byte reproducible.
"""

from __future__ import annotations

from case_notes_eval import RecordingChecker

CHECKER = RecordingChecker()


def test_bare_interpretation_is_flagged() -> None:
    result = CHECKER.check("Jamie was being manipulative and attention-seeking.")
    assert result.matches, "an interpretation stated as fact should flag"


def test_observation_is_not_flagged() -> None:
    # A pure behavioural description carries no emotional labels to flag.
    result = CHECKER.check(
        "Jamie asked three times whether the visit was cancelled, then went to his room."
    )
    assert result.matches == []


def test_quoted_speech_is_suppressed() -> None:
    # The child's own words are evidence and must never be flagged.
    quoted = CHECKER.check('Jamie said "I am so angry" and sat down.')
    assert not any(m.matched_text.lower() == "angry" for m in quoted.matches)
    assert any(s["reason"] == "quoted_speech" for s in quoted.suppressed)


def test_qualifier_suppresses() -> None:
    # "appeared angry" is good practice: an observation, not a stated fact.
    qualified = CHECKER.check("Jamie appeared angry when the visit was cancelled.")
    assert not any(m.matched_text.lower() == "angry" and not m.downgraded for m in qualified.matches)


def test_trailing_evidence_downgrades() -> None:
    # "angry when X" cites evidence; severity drops one step rather than clearing.
    # The surface form is "was angry"; the canonical phrase is "angry".
    result = CHECKER.check("He was angry when the chair fell over.")
    angry = [m for m in result.matches if m.phrase == "angry"]
    assert angry and angry[0].downgraded


def test_empty_note_is_clean() -> None:
    assert CHECKER.check("").matches == []
    assert CHECKER.check("   ").matches == []


def test_deterministic_across_runs() -> None:
    note = "Jamie was aggressive and manipulative; he appeared upset when told no."
    first = CHECKER.check(note).to_dict()
    for _ in range(20):
        assert CHECKER.check(note).to_dict() == first
