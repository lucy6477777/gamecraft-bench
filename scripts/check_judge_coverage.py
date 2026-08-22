#!/usr/bin/env python3
"""Refuse to trust a reward that the judge did not actually produce.

reward.txt can only carry a number, and the task wrapper rewrites a missing one
to 0 before exiting 0, so there is no channel through which "scoring failed"
can reach the harness -- every infrastructure failure arrives as "this game
scored 0". Aggregation has to make that distinction itself, from the artifacts.

Two signatures are reported:

  sentinel   JUDGE_INCOMPLETE.json, written by the current verifier.
  legacy     the shape the defect left before that existed: judge calls
             errored, so some demo contributed a fabricated 0.0. Partial is not
             milder than total -- the first real case scored 0.106 with one
             failed call where the same artifact scored 0.265 with none.

    python scripts/check_judge_coverage.py <jobs-root> [...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _verifier_dirs(root: Path):
    """Every directory under root that holds a breakdown.json.

    Not just harbor's `<trial>/verifier/` layout: scores produced by invoking
    the verifier directly land one level down, and a checker that silently
    finds nothing is worse than one that errors -- it reads as "all clean".
    """
    if (root / "breakdown.json").is_file():
        yield root
        return
    seen: set[Path] = set()
    for f in sorted(root.rglob("breakdown.json")):
        d = f.parent
        if d not in seen:
            seen.add(d)
            yield d


def inspect(vd: Path) -> dict:
    bd = json.loads((vd / "breakdown.json").read_text())
    cov = bd.get("judge_coverage")
    judge_errs = [e for e in bd.get("errors", []) if e.startswith("judge failed")]
    reqs = bd.get("requirements", [])
    all_zero = bool(reqs) and all(r.get("aggregated") == 0.0 for r in reqs)

    if (vd / "JUDGE_INCOMPLETE.json").is_file():
        verdict = "INCOMPLETE"
    elif cov is not None:
        verdict = "ok" if cov.get("complete") else "INCOMPLETE"
    elif judge_errs:
        verdict = "LEGACY-ZEROED" if (bd.get("build_ok") and all_zero) else "LEGACY-PARTIAL"
    else:
        verdict = "ok (no coverage data)" if cov is None else "ok"

    return {"dir": vd, "reward": bd.get("reward"), "build_ok": bd.get("build_ok"),
            "verdict": verdict, "judge_errors": len(judge_errs),
            "demos": len(bd.get("demos", [])),
            "coverage": (f"{cov['demos_judged']}/{cov['demos_total']}"
                         if cov else "-")}


def main() -> int:
    roots = [Path(a) for a in sys.argv[1:]] or [Path.cwd()]
    rows = [inspect(vd) for root in roots for vd in _verifier_dirs(root)]
    if not rows:
        print("no breakdown.json found", file=sys.stderr)
        return 2

    print(f"{'verdict':<22}{'reward':>8}{'cov':>7}{'jerr':>6}  trial")
    for r in rows:
        trial = r["dir"].parent.name if r["dir"].name == "verifier" else r["dir"].name
        rw = "-" if r["reward"] is None else f"{r['reward']:.4f}"
        print(f"{r['verdict']:<22}{rw:>8}{r['coverage']:>7}"
              f"{r['judge_errors']:>6}  {trial}")

    # Any fabricated zero disqualifies the number, whether it took out one demo
    # or all of them.
    bad = [r for r in rows if r["verdict"].startswith(("INCOMPLETE", "LEGACY"))]
    print(f"\n{len(rows)} trial(s); {len(bad)} must not be aggregated.")
    for r in bad:
        print(f"  ! {r['dir']}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
