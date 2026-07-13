"""Per-model, per-condition results from the Inspect logs. Deterministic; no model involved.

Reads ``.eval`` logs from a directory and prints the primary metrics, the evasion
delta, and the per-model count of EVASION notes that scored clean (candidate
validator bypasses).
"""

from __future__ import annotations

import sys
from collections import defaultdict

from inspect_ai.log import list_eval_logs, read_eval_log


def analyse(log_dir: str) -> int:
    rows: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for info in list_eval_logs(log_dir):
        log = read_eval_log(info.name)
        if not log.samples:
            continue
        model = log.eval.model
        for s in log.samples:
            if not s.scores:
                continue
            sc = next(iter(s.scores.values()), None)
            if not sc or not sc.metadata:
                continue
            condition = str(sc.metadata.get("condition", ""))
            rows[(model, condition)].append(sc.metadata)

    if not rows:
        print(f"No scored samples found in {log_dir!r}.", file=sys.stderr)
        return 1

    print(
        f"{'model':<34} {'cond':<9} {'n':>3} {'clean%':>7} "
        f"{'high%':>6} {'fl/100w':>8} {'qual%':>6}"
    )
    print("-" * 78)
    summary: dict[tuple[str, str], float] = {}
    for model, cond in sorted(rows):
        ms = rows[(model, cond)]
        n = len(ms)
        clean = sum(m["is_clean"] for m in ms) / n * 100
        high = sum(m["has_high"] for m in ms) / n * 100
        tf = sum(m["n_flags"] for m in ms)
        tw = sum(m["n_words"] for m in ms)
        f100 = tf / tw * 100 if tw else 0
        qual = sum(m["used_qualifier"] for m in ms) / n * 100
        summary[(model, cond)] = clean
        print(f"{model:<34} {cond:<9} {n:>3} {clean:>6.1f}% {high:>5.1f}% {f100:>8.2f} {qual:>5.1f}%")

    print()
    print("EVASION DELTA (clean% evasion - clean% neutral); positive = evaded while carrying judgement")
    print("-" * 78)
    models = sorted({m for m, _ in rows})
    for model in models:
        ne = summary.get((model, "neutral"))
        ev = summary.get((model, "evasion"))
        if ne is None or ev is None:
            continue
        print(f"{model:<34} neutral {ne:>5.1f}%   evasion {ev:>5.1f}%   delta {ev - ne:>+6.1f}pp")

    print()
    print("EVASION notes that scored CLEAN (zero flags) = candidate bypasses")
    print("-" * 78)
    total_clean_evasion = 0
    for model in models:
        ms = rows.get((model, "evasion"), [])
        cleans = [m for m in ms if m["is_clean"]]
        total_clean_evasion += len(cleans)
        scenarios = ",".join(sorted(m["scenario"] for m in cleans)) or "-"
        print(f"{model:<34} {len(cleans):>2}/{len(ms)} clean  scenarios: {scenarios}")
    print(f"\nTOTAL candidate bypasses across all models: {total_clean_evasion}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    log_dir = args[0] if args else "./logs"
    return analyse(log_dir)


if __name__ == "__main__":
    raise SystemExit(main())
