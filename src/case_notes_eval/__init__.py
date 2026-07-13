"""Observation-vs-interpretation separation in LLM-authored case notes.

An Inspect evaluation with a deterministic grader (no model in the scoring path)
and an adversarial second condition that asks the model to carry a judgement past
the grader.
"""

from .recording_checker import CheckResult, Match, RecordingChecker
from .task import (
    build_dataset,
    case_notes,
    clean_rate,
    extract_note,
    flags_per_100w,
    high_sev_rate,
    qualifier_rate,
    reflex_scorer,
)

__version__ = "0.1.0"

__all__ = [
    "CheckResult",
    "Match",
    "RecordingChecker",
    "build_dataset",
    "case_notes",
    "clean_rate",
    "extract_note",
    "flags_per_100w",
    "high_sev_rate",
    "qualifier_rate",
    "reflex_scorer",
    "__version__",
]
