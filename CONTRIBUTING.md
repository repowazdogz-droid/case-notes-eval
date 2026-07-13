# Contributing

This is a study repository. Its value is that the grader is deterministic and the
rubric was fixed before the first model call, so the bar for changes is unusual.

## Principles

- **Do not edit `docs/RUBRIC.md` above the Amendment line.** It is a pre-registration.
  A pre-registration that is silently rewritten to match later results is worthless.
  Corrections are appended as dated amendments; the original text stands.
- **No model in the scoring path.** The primary metrics must stay deterministic. Any
  metric that needs a judge is secondary, reported separately, and labelled as weak.
- **The grader must stay byte-for-byte reproducible.** A test enforces it; keep it.
- **Scenarios and lexicon are synthetic and authored.** Do not add real records.

## Dev loop

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```

All three run in CI on Python 3.11–3.13. Please keep lint and types green without
disabling error classes.
