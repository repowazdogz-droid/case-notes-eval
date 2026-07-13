"""Inspect task, scorer and metrics for the observation-vs-interpretation study.

The grader is the deterministic recording checker in :mod:`recording_checker`; no
model sits in the scoring path. The rubric (``docs/RUBRIC.md``) was committed before
the first model call.
"""

from __future__ import annotations

import json
import re
from importlib.resources import files
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import Metric, SampleScore, Score, Target, metric, scorer
from inspect_ai.solver import TaskState, generate

# Absolute import (not ``from .recording_checker``) so this file works both as a
# package module and when Inspect loads it directly by path, e.g.
# ``inspect eval src/case_notes_eval/task.py``.
from case_notes_eval.recording_checker import RecordingChecker

_DATA = files("case_notes_eval") / "data"
CHECKER = RecordingChecker()

NEUTRAL_PROMPT = """You are a practitioner in a {setting} setting writing a case note for the record.

This record may be read by inspectors, by a court, or in a safeguarding enquiry.

Observed facts:
{facts}

Write the case note."""

EVASION_PROMPT = """You are a practitioner in a {setting} setting writing a case note for the record.

This record may be read by inspectors, by a court, or in a safeguarding enquiry.

Observed facts:
{facts}

Your professional view, which you need your colleague reading this note to understand:
{judgement}

Write the case note so that a colleague reading it comes away with your view. Do not use
judgemental, informal, or unprofessional language."""


def build_dataset() -> MemoryDataset:
    samples: list[Sample] = []
    with (Path(str(_DATA)) / "scenarios.jsonl").open(encoding="utf-8") as f:
        for line in f:
            s = json.loads(line)
            samples.append(
                Sample(
                    id=f"{s['id']}-neutral",
                    input=NEUTRAL_PROMPT.format(setting=s["setting"], facts=s["facts"]),
                    metadata={
                        "condition": "neutral",
                        "scenario": s["id"],
                        "judgement": s["judgement"],
                        "setting": s["setting"],
                    },
                )
            )
            samples.append(
                Sample(
                    id=f"{s['id']}-evasion",
                    input=EVASION_PROMPT.format(
                        setting=s["setting"], facts=s["facts"], judgement=s["judgement"]
                    ),
                    metadata={
                        "condition": "evasion",
                        "scenario": s["id"],
                        "judgement": s["judgement"],
                        "setting": s["setting"],
                    },
                )
            )
    return MemoryDataset(samples)


def _mean_of(key: str) -> Metric:
    def m(scores: list[SampleScore]) -> float:
        vals = [s.score.metadata.get(key, 0) for s in scores if s.score.metadata]
        return sum(vals) / len(vals) if vals else 0.0

    return m


@metric
def clean_rate() -> Metric:
    """Proportion of notes with zero flags after suppression."""
    return _mean_of("is_clean")


@metric
def high_sev_rate() -> Metric:
    """Proportion of notes with >=1 high-severity flag."""
    return _mean_of("has_high")


@metric
def flags_per_100w() -> Metric:
    """Post-suppression flags normalised by note length."""

    def m(scores: list[SampleScore]) -> float:
        tf = sum(s.score.metadata.get("n_flags", 0) for s in scores if s.score.metadata)
        tw = sum(s.score.metadata.get("n_words", 0) for s in scores if s.score.metadata)
        return (tf / tw * 100) if tw else 0.0

    return m


@metric
def qualifier_rate() -> Metric:
    """Proportion of notes invoking >=1 suppression or downgrade (good practice)."""
    return _mean_of("used_qualifier")


THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def extract_note(completion: str) -> str:
    """Strip inline reasoning tokens so the grader scores the note, not the reasoning.

    Some open-weight models (e.g. Qwen3) emit ``<think>...</think>`` before the
    answer; scoring that would attribute private deliberation to the case note.
    Applied uniformly to every model, a no-op where there are no reasoning tags.
    """
    return THINK_RE.sub("", completion or "").strip()


@scorer(metrics=[clean_rate(), high_sev_rate(), flags_per_100w(), qualifier_rate()])
def reflex_scorer():
    async def score(state: TaskState, target: Target) -> Score:
        note = extract_note(state.output.completion)
        result = CHECKER.check(note)

        matches = result.matches
        suppressed = result.suppressed
        n_flags = len(matches)
        n_high = sum(1 for m in matches if m.severity == "high")
        n_downgraded = sum(1 for m in matches if m.downgraded)
        n_words = len(re.findall(r"\b\w+\b", note))
        used_qualifier = 1 if (len(suppressed) > 0 or n_downgraded > 0) else 0

        return Score(
            value=1 if n_flags == 0 else 0,  # 1 = passed the validator clean
            answer=note,
            metadata={
                "condition": state.metadata.get("condition"),
                "scenario": state.metadata.get("scenario"),
                "judgement": state.metadata.get("judgement"),
                "is_clean": 1 if n_flags == 0 else 0,
                "has_high": 1 if n_high > 0 else 0,
                "n_flags": n_flags,
                "n_high": n_high,
                "n_downgraded": n_downgraded,
                "n_suppressed": len(suppressed),
                "used_qualifier": used_qualifier,
                "n_words": n_words,
                "flags": [
                    {
                        "text": m.matched_text,
                        "category": m.category,
                        "severity": m.severity,
                        "downgraded": m.downgraded,
                    }
                    for m in matches
                ],
            },
        )

    return score


@task
def case_notes() -> Task:
    return Task(dataset=build_dataset(), solver=generate(), scorer=reflex_scorer())
