#!/usr/bin/env python3
"""Measure the judge's run-to-run variance on identical evidence.

Re-scores the demos of a finished job N times with the configured judge and the
same rubric, changing nothing else. Everything the judge sees is byte-identical
across runs, so any spread in the resulting scores is judge noise.

Why this matters: without it, a difference between two runs cannot be attributed.
This repo has already produced two cases where an identical artifact scored
differently because of infrastructure, not quality, so "it went up by X" is not
a claim that can be made before the noise band is known.

    python scripts/judge_noise.py --job <jobs>/<ts>/<trial> --runs 3
"""
from __future__ import annotations

import argparse
import glob
import json
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from gamecraft_bench.verifier.judges import get_judge  # noqa: E402
from gamecraft_bench.verifier.judges.base import (  # noqa: E402
    JudgeRequest,
    RequirementSpec,
)


def _demos(job: Path) -> list[tuple[str, Path | None, list[Path]]]:
    out = []
    for d in sorted(glob.glob(str(job / "verifier" / "demos" / "*") + "/")):
        p = Path(d)
        frames = sorted(p.glob("frames/*.png")) or sorted(p.glob("frames/*.jpg"))
        mp4 = next(iter(p.glob("*.mp4")), None)
        if frames:
            out.append((p.name, mp4, frames))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True, type=Path,
                    help="a finished trial dir (the one containing verifier/)")
    ap.add_argument("--rubric", type=Path, default=None,
                    help="defaults to the rubric of the task named in the trial dir")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", type=Path,
                    default=Path("/home/tiger/gamecraft-bench-jobs/judge_noise.json"))
    args = ap.parse_args()

    rubric_path = args.rubric
    if rubric_path is None:
        task = args.job.name.split("__")[0]
        rubric_path = REPO / "tasks" / task / "tests" / "rubric.json"
    rubric = json.loads(rubric_path.read_text())
    reqs = [RequirementSpec(id=r["id"], description=r["description"])
            for r in rubric["requirements"]]

    demos = _demos(args.job)
    if not demos:
        print(f"no demos with frames under {args.job}", file=sys.stderr)
        return 1

    judge = get_judge()
    print(f"judge   = {judge!r}")
    print(f"rubric  = {rubric_path}  ({len(reqs)} requirements)")
    print(f"demos   = {len(demos)}  ({', '.join(d[0] for d in demos)})")
    print(f"runs    = {args.runs}\n")

    runs: list[dict[str, dict[str, float]]] = []
    errors: list[str] = []
    for r in range(args.runs):
        per_demo: dict[str, dict[str, float]] = {}
        for demo_id, mp4, frames in demos:
            t0 = time.time()
            try:
                resp = judge.score(JudgeRequest(demo_id=demo_id, video_path=mp4,
                                                frame_paths=frames, requirements=reqs))
                per_demo[demo_id] = dict(resp.scores)
                print(f"  run {r + 1}  {demo_id:<22} ok    {time.time() - t0:6.1f}s")
            except Exception as exc:  # noqa: BLE001 - report, do not mask
                msg = f"run {r + 1} {demo_id}: {type(exc).__name__}: {exc}"
                errors.append(msg)
                print(f"  run {r + 1}  {demo_id:<22} FAIL  {type(exc).__name__}: "
                      f"{str(exc)[:80]}")
        runs.append(per_demo)

    # spread per (demo, requirement), across runs
    rows = []
    for demo_id, _, _ in demos:
        for req in reqs:
            vals = [run[demo_id][req.id] for run in runs
                    if demo_id in run and req.id in run[demo_id]]
            if len(vals) < 2:
                continue
            rows.append({"demo": demo_id, "req": req.id, "values": vals,
                         "mean": statistics.mean(vals),
                         "range": max(vals) - min(vals),
                         "stdev": statistics.pstdev(vals)})

    args.out.write_text(json.dumps(
        {"judge": repr(judge), "rubric": str(rubric_path), "runs": runs,
         "per_requirement": rows, "errors": errors}, indent=1))

    if rows:
        spreads = [r["range"] for r in rows]
        print(f"\n--- noise band over {len(rows)} (demo, requirement) pairs ---")
        print(f"  mean range   {statistics.mean(spreads):.3f}")
        print(f"  median range {statistics.median(spreads):.3f}")
        print(f"  p90 range    {sorted(spreads)[int(len(spreads) * 0.9)]:.3f}")
        print(f"  max range    {max(spreads):.3f}")
        print(f"  identical    {sum(1 for s in spreads if s == 0)}/{len(spreads)}")
        worst = sorted(rows, key=lambda r: -r["range"])[:6]
        print("\n  widest spreads:")
        for w in worst:
            print(f"    {w['demo']:<22} {w['req']:<4} {w['values']}  range {w['range']:.2f}")
    if errors:
        print(f"\n  {len(errors)} judge call(s) failed:")
        for e in errors[:5]:
            print(f"    {e[:110]}")
    print(f"\nsaved -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
