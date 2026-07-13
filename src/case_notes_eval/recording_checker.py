"""
recording_checker — deterministic language checker for UK children's social care
and safeguarding case notes.

Pure Python 3.9+, standard library only. No AI at runtime. Drop the `src` and
`data` folders into any project (including a Reflex app) and call `check()`.

Pipeline per call:
  1. Locate quoted spans (child's own words) -> matches inside are suppressed.
  2. Run one compiled word-boundary regex over the lower-cased text.
  3. Apply qualifier suppression ("appeared upset when..." is good practice).
  4. Apply trailing-evidence downgrade ("upset after X" -> severity lowered).
  5. Apply the never_flag safelist.
  6. Return structured matches with spans, category, severity, why, suggestion.

Typical usage:
    from recording_checker import RecordingChecker
    checker = RecordingChecker()                      # loads bundled data
    result = checker.check("He kicked off for no reason.")
    for m in result.matches:
        print(m.matched_text, m.category, m.severity, m.suggestion)
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"

SEVERITY_ORDER = {"high": 3, "medium": 2, "low": 1}
_DOWNGRADE = {"high": "medium", "medium": "low", "low": "low"}


@dataclass
class Match:
    start: int                # char offset in original text
    end: int                  # char offset (exclusive)
    matched_text: str         # text as it appeared in the note
    phrase: str               # canonical phrase from the dataset
    category: str
    severity: str             # possibly downgraded by evidence rule
    original_severity: str
    why: str
    suggestion: str
    downgraded: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CheckResult:
    text: str
    matches: list[Match] = field(default_factory=list)
    suppressed: list[dict] = field(default_factory=list)  # audit trail

    @property
    def counts_by_severity(self) -> dict[str, int]:
        out = {"high": 0, "medium": 0, "low": 0}
        for m in self.matches:
            out[m.severity] += 1
        return out

    @property
    def counts_by_category(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for m in self.matches:
            out[m.category] = out.get(m.category, 0) + 1
        return out

    def to_dict(self) -> dict:
        return {
            "matches": [m.to_dict() for m in self.matches],
            "suppressed": self.suppressed,
            "counts_by_severity": self.counts_by_severity,
            "counts_by_category": self.counts_by_category,
        }


class RecordingChecker:
    def __init__(
        self,
        phrases_path: Path | None = None,
        rules_path: Path | None = None,
        enabled_categories: set[str] | None = None,
        min_severity: str = "low",
    ):
        phrases_path = Path(phrases_path or _DATA_DIR / "flagged_phrases.json")
        rules_path = Path(rules_path or _DATA_DIR / "suppression_rules.json")

        with open(phrases_path, encoding="utf-8") as f:
            self.entries: list[dict] = json.load(f)
        with open(rules_path, encoding="utf-8") as f:
            self.rules: dict = json.load(f)

        self.enabled_categories = enabled_categories  # None = all
        self.min_severity = min_severity

        self._pattern, self._lookup = self._compile(self.entries)
        self._qualifier_re = self._compile_qualifiers()
        never_terms = [t.lower() for t in self.rules.get("never_flag", {}).get("terms", [])]
        self._never_flag = set(never_terms)
        self._never_flag_re = (
            re.compile(
                r"(?<!\w)("
                + "|".join(self._form_regex(t) for t in sorted(never_terms, key=len, reverse=True))
                + r")(?!\w)",
                re.IGNORECASE,
            )
            if never_terms
            else None
        )

    # ------------------------------------------------------------------ build

    @staticmethod
    def _surface_forms(entry: dict) -> list[str]:
        forms = [entry["phrase"]] + list(entry.get("variants", []))
        # Drop template-style variants like "just being [name]" — not literally matchable.
        return [f for f in forms if "[" not in f]

    def _compile(self, entries: list[dict]):
        lookup: dict[str, dict] = {}
        forms: list[str] = []
        for e in entries:
            for form in self._surface_forms(e):
                key = form.lower()
                # First definition wins; dataset is de-duplicated upstream.
                if key not in lookup:
                    lookup[key] = e
                    forms.append(key)
        # Longest-first so "completely out of control" beats "out of control".
        forms.sort(key=len, reverse=True)
        alternation = "|".join(self._form_regex(f) for f in forms)
        pattern = re.compile(r"(?<!\w)(" + alternation + r")(?!\w)", re.IGNORECASE)
        return pattern, lookup

    @staticmethod
    def _form_regex(form: str) -> str:
        """Escape a surface form; let any run of whitespace/hyphen match between words,
        and treat straight/curly apostrophes interchangeably."""
        parts = re.split(r"\s+", form.strip())
        escaped = []
        for p in parts:
            p = re.escape(p)
            p = p.replace(r"\'", "['\u2019]").replace("'", "['\u2019]")
            escaped.append(p)
        return r"[\s\-]+".join(escaped)

    def _compile_qualifiers(self):
        q = self.rules.get("qualifier_suppression", {})
        if not q.get("enabled"):
            return None
        alts = sorted(q.get("qualifiers", []), key=len, reverse=True)
        if not alts:
            return None
        joined = "|".join(re.escape(a) for a in alts)
        return re.compile(r"(?<!\w)(" + joined + r")(?!\w)", re.IGNORECASE)

    # ------------------------------------------------------------- quote spans

    def _quoted_spans(self, text: str) -> list[tuple[int, int]]:
        cfg = self.rules.get("quote_suppression", {})
        if not cfg.get("enabled"):
            return []
        spans: list[tuple[int, int]] = []
        for open_q, close_q in cfg.get("quote_pairs", []):
            if open_q == close_q:
                # Pair identical quote chars left-to-right. For the straight
                # apostrophe, only treat it as a quote when not inside a word
                # (so "wouldn't ... child's" doesn't create a fake span).
                if open_q == "'":
                    positions = [
                        m.start()
                        for m in re.finditer(r"(?<![A-Za-z])'|'(?![A-Za-z])", text)
                    ]
                else:
                    positions = [i for i, ch in enumerate(text) if ch == open_q]
                # Odd trailing quote has no partner; strict=False drops it by design.
                for a, b in zip(positions[0::2], positions[1::2], strict=False):
                    spans.append((a, b + 1))
            else:
                start = None
                for i, ch in enumerate(text):
                    if ch == open_q and start is None:
                        start = i
                    elif ch == close_q and start is not None:
                        spans.append((start, i + 1))
                        start = None
        return spans

    @staticmethod
    def _in_spans(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
        return any(start >= a and end <= b for a, b in spans)

    # ---------------------------------------------------------------- checking

    def check(self, text: str) -> CheckResult:
        result = CheckResult(text=text)
        if not text or not text.strip():
            return result

        quoted = self._quoted_spans(text)
        protected = (
            [(m.start(1), m.end(1)) for m in self._never_flag_re.finditer(text)]
            if self._never_flag_re
            else []
        )
        q_cfg = self.rules.get("qualifier_suppression", {})
        t_cfg = self.rules.get("trailing_evidence_suppression", {})
        q_cats = set(q_cfg.get("applies_to_categories", []))
        t_cats = set(t_cfg.get("applies_to_categories", []))
        q_window = int(q_cfg.get("window_words", 4))
        t_window = int(t_cfg.get("window_words", 2))
        connectives = {c.lower() for c in t_cfg.get("connectives", [])}

        taken: list[tuple[int, int]] = []

        for m in self._pattern.finditer(text):
            start, end = m.start(1), m.end(1)
            surface = m.group(1)
            entry = self._lookup.get(re.sub(r"[\s\-]+", " ", surface.lower()).replace("\u2019", "'"))
            if entry is None:
                continue

            # Overlap guard (longest-first ordering makes first match win).
            if any(not (end <= a or start >= b) for a, b in taken):
                continue

            cat, sev = entry["category"], entry["severity"]

            if self.enabled_categories is not None and cat not in self.enabled_categories:
                continue
            if SEVERITY_ORDER[sev] < SEVERITY_ORDER[self.min_severity]:
                continue
            if surface.lower() in self._never_flag or any(
                start >= a and end <= b for a, b in protected
            ):
                result.suppressed.append(
                    {"matched_text": surface, "phrase": entry["phrase"], "reason": "never_flag_safelist"}
                )
                continue

            # 1) Quoted speech — always good practice, never flag.
            if self._in_spans(start, end, quoted):
                result.suppressed.append(
                    {"matched_text": surface, "phrase": entry["phrase"], "reason": "quoted_speech"}
                )
                continue

            # 2) Qualifier suppression ("appeared", "seemed", "presented as"...)
            if self._qualifier_re and cat in q_cats:
                preceding = text[max(0, start - 80):start]
                words_before = preceding.split()
                tail = " ".join(words_before[-q_window:]) if words_before else ""
                if tail and self._qualifier_re.search(tail):
                    result.suppressed.append(
                        {"matched_text": surface, "phrase": entry["phrase"], "reason": "qualified_observation"}
                    )
                    continue

            downgraded = False
            final_sev = sev

            # 3) Trailing evidence ("upset after...", "angry when...") -> downgrade.
            if t_cfg.get("enabled") and cat in t_cats:
                following = text[end:end + 60].split()
                if any(w.strip(".,;:!?").lower() in connectives for w in following[:t_window]):
                    final_sev = _DOWNGRADE[sev]
                    downgraded = True

            taken.append((start, end))
            result.matches.append(
                Match(
                    start=start,
                    end=end,
                    matched_text=surface,
                    phrase=entry["phrase"],
                    category=cat,
                    severity=final_sev,
                    original_severity=sev,
                    why=entry["why"],
                    suggestion=entry["suggestion"],
                    downgraded=downgraded,
                )
            )

        result.matches.sort(key=lambda x: x.start)
        return result


# --------------------------------------------------------------------- CLI

def _main() -> None:
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="Check a case note for subjective/judgemental language.")
    ap.add_argument("file", nargs="?", help="Text file to check (reads stdin if omitted)")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of a readable report")
    ap.add_argument("--min-severity", default="low", choices=["low", "medium", "high"])
    args = ap.parse_args()

    text = open(args.file, encoding="utf-8").read() if args.file else sys.stdin.read()
    checker = RecordingChecker(min_severity=args.min_severity)
    result = checker.check(text)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return

    if not result.matches:
        print("No flagged language found.")
        return
    print(f"{len(result.matches)} issue(s) found "
          f"(high: {result.counts_by_severity['high']}, "
          f"medium: {result.counts_by_severity['medium']}, "
          f"low: {result.counts_by_severity['low']})\n")
    for m in result.matches:
        flag = " (downgraded: evidence follows)" if m.downgraded else ""
        print(f"[{m.severity.upper()}] {m.category}: \"{m.matched_text}\"{flag}")
        print(f"  why: {m.why}")
        print(f"  try: {m.suggestion}\n")


if __name__ == "__main__":
    _main()
