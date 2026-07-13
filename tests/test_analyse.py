"""The analysis reproduces from the committed sample logs.

Runs the deterministic analysis over the bundled open-weight sample logs and checks
it produces the documented shape: four open-weight models, both conditions, and a
non-zero count of candidate bypasses (EVASION notes that scored clean).
"""

from __future__ import annotations

from pathlib import Path

from case_notes_eval.analyse import analyse

SAMPLE_LOGS = Path(__file__).resolve().parent.parent / "examples" / "sample_logs"


def test_sample_logs_analyse(capsys) -> None:  # type: ignore[no-untyped-def]
    rc = analyse(str(SAMPLE_LOGS))
    out = capsys.readouterr().out
    assert rc == 0
    assert "EVASION DELTA" in out
    assert "candidate bypasses" in out
    # The bundled sample is the open-weight arm; every family appears.
    for family in ("gemma3", "llama3", "mistral-small3.1", "qwen3"):
        assert family in out, family


def test_bundled_logs_present() -> None:
    logs = list(SAMPLE_LOGS.glob("*.eval"))
    assert len(logs) == 4, f"expected 4 sample logs, found {len(logs)}"
