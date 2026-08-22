#!/usr/bin/env python3
"""Re-score a finished trial from the frames it already recorded.

Replay is the expensive, environment-bound half of scoring and it is also the
deterministic half: the frames on disk are the evidence. When the judge path
changes -- a budget, a frame selection, a model -- the honest way to measure
the change is to feed the identical frames through the new path, so the only
variable is the one under test.

That is also how the two worst defects in this repo were proven: an artifact
that scored 0.000 rejudged to 0.481, and one that scored 0.122 rejudged to
0.458, in both cases without a byte of the game changing.

    python scripts/rejudge.py --job <trial-dir> [--rubric <path>] [--out <dir>]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from gamecraft_bench.verifier.judges import JudgeError, get_judge  # noqa: E402
from gamecraft_bench.verifier.judges.base import (  # noqa: E402
    JudgeRequest, RequirementSpec,
)
from gamecraft_bench.verifier.score import (  # noqa: E402
    _JUDGE_MAX_ATTEMPTS, RequirementScore, ScoreResult, DemoArtifacts,
    _aggregate, _safe_eval_formula, _validate_agg, _write_artifacts,
)


def _demos(job: Path) -> list[tuple[str, Path | None, list[Path]]]:
    out = []
    root = job / "verifier" / "demos" if (job / "verifier").is_dir() else job / "demos"
    for p in sorted(d for d in root.glob("*") if d.is_dir()):
        frames = sorted(p.glob("frames/*.png")) or sorted(p.glob("frames/*.jpg"))
        if frames:
            out.append((p.name, next(iter(p.glob("*.mp4")), None), frames))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True, type=Path)
    ap.add_argument("--rubric", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None,
                    help="defaults to <job>/verifier_rejudged")
    ap.add_argument("--tasks-dir", default="tasks",
                    help="where to look up the rubric by task name")
    args = ap.parse_args()

    job = args.job.resolve()
    rubric_path = args.rubric
    if rubric_path is None:
        task = job.name.split("__")[0]
        rubric_path = REPO / args.tasks_dir / task / "tests" / "rubric.json"
    rubric = json.loads(rubric_path.read_text())
    requirements = rubric["requirements"]
    formula = rubric["score_formula"]
    build_id = rubric["build_check"].get("id", "BUILD")

    demos = _demos(job)
    if not demos:
        print(f"no demos with frames under {job}", file=sys.stderr)
        return 1

    # The build gate is a property of the artifact, not of judging. Carry the
    # original verdict forward rather than silently assuming it passed.
    prev = job / "verifier" / "breakdown.json"
    build_ok = json.loads(prev.read_text()).get("build_ok", True) if prev.is_file() else True

    judge = get_judge()
    out_dir = (args.out or job / "verifier_rejudged").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"job     = {job}")
    print(f"rubric  = {rubric_path}  ({len(requirements)} requirements)")
    print(f"judge   = {judge!r}")
    print(f"demos   = {len(demos)}   build_ok = {build_ok}\n")

    specs = [RequirementSpec(id=r["id"], description=r["description"]) for r in requirements]
    req_scores = {r["id"]: RequirementScore(requirement_id=r["id"],
                                            description=r["description"],
                                            per_demo={}, aggregated=0.0,
                                            agg=_validate_agg(r)) for r in requirements}
    judge_log: list[dict] = []
    errors: list[str] = []
    unjudged: list[str] = []
    artifacts: list[DemoArtifacts] = []

    for demo_id, mp4, frames in demos:
        artifacts.append(DemoArtifacts(demo_id=demo_id, trace_path=Path(""),
                                       mp4_path=mp4 or Path(""),
                                       frame_paths=frames, duration_seconds=0.0))
        if not build_ok:
            continue
        req = JudgeRequest(demo_id=demo_id, video_path=mp4,
                           frame_paths=frames, requirements=specs)
        t0 = time.time()
        last: JudgeError | None = None
        scores: dict = {}
        rationales: dict = {}
        raw = ""
        for attempt in range(_JUDGE_MAX_ATTEMPTS):
            try:
                resp = judge.score(req)
                scores, rationales, raw = resp.scores, resp.rationales, resp.raw
                last = None
                break
            except JudgeError as e:
                last = e
        dt = time.time() - t0
        if last is not None:
            unjudged.append(demo_id)
            errors.append(f"judge failed on {demo_id}: {last}")
            judge_log.append({"demo_id": demo_id, "requirement_id": None,
                              "score": None, "rationale": "", "raw": "",
                              "error": str(last), "latency_seconds": round(dt, 3)})
            print(f"  {demo_id:<24} FAILED  {dt:5.1f}s")
            continue
        for r in requirements:
            rid = r["id"]
            try:
                sc = max(0.0, min(1.0, float(scores.get(rid, 0.0))))
            except (TypeError, ValueError):
                sc = 0.0
                errors.append(f"non-numeric score for {demo_id}/{rid}")
            judge_log.append({"demo_id": demo_id, "requirement_id": rid, "score": sc,
                              "rationale": rationales.get(rid, ""),
                              "raw": raw if rid == requirements[0]["id"] else "",
                              "latency_seconds": round(dt, 3)})
            cur = req_scores[rid]
            pd = {**cur.per_demo, demo_id: sc}
            req_scores[rid] = dataclasses.replace(cur, per_demo=pd,
                                                  aggregated=_aggregate(cur.agg, pd))
        print(f"  {demo_id:<24} ok      {dt:5.1f}s   ({len(frames)} frames on disk)")

    variables = {build_id: 1.0 if build_ok else 0.0}
    variables.update({rid: rs.aggregated for rid, rs in req_scores.items()})
    reward = max(0.0, min(1.0, _safe_eval_formula(formula, variables)))

    result = ScoreResult(reward=reward, build_ok=build_ok, build_log="(carried forward)",
                         formula=formula, requirements=list(req_scores.values()),
                         demos=artifacts, judge_name=type(judge).__name__,
                         judge_model=judge.model, errors=errors,
                         unjudged_demos=unjudged,
                         replay_engine="(rejudged from recorded frames)")
    _write_artifacts(out_dir, result, judge_log, variables)
    (out_dir / "reward.txt").write_text(f"{reward:.6f}\n")

    old = json.loads(prev.read_text())["reward"] if prev.is_file() else None
    print(f"\n  reward   {reward:.4f}" + (f"   (was {old:.4f}, delta {reward-old:+.4f})" if old is not None else ""))
    if unjudged:
        print(f"  INCOMPLETE: {len(unjudged)} demo(s) unjudged -- reward unreliable")
    print(f"  wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
