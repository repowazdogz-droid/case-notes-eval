# Changelog

All notable changes to this project are documented here. The format is loosely based
on [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] — 2026-07-13

First release.

### Added
- Inspect task, deterministic scorer, and four grader-computed metrics for
  observation-vs-interpretation separation in LLM-authored case notes.
- The `recording_checker` grader (252-phrase lexicon, quote suppression,
  observational-qualifier suppression, trailing-evidence downgrade); no model in the
  scoring path.
- 30 synthetic scenarios in two conditions (neutral, evasion).
- `docs/RUBRIC.md`, the pre-registration, reproduced unedited including its dated
  Amendment 3 factual correction (Reflex was a demo, never used on real records).
- `case-notes-analyse` and `case-notes-check` CLIs.
- Four committed open-weight sample logs so the analysis runs with no model and no
  API key.
- Tests for the deterministic grader (including reproducibility) and for the analysis
  over the bundled sample logs.

### Guarantees
- The grader is byte-for-byte reproducible on the same input (test-enforced).
- The primary metrics have no model in the scoring path.
