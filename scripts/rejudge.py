#!/usr/bin/env python3
"""Score an already-generated run, on a machine that never built the games.

The generation sweep runs with GAMECRAFT_BENCH_JUDGE=stub: it builds each
project and replays every demo under Xvfb -- both local and free -- but skips
the paid multimodal scoring. That leaves a complete set of mp4s and sampled
frames in <trial>/verifier/demos/, which is all the judge ever looks at. This
script picks those up on the judging machine, calls the real judge, and
recomputes the rubric formula.

    OPENROUTER_API_KEY=... \
    ./rejudge.py <job-dir> --judge openai --judge-model openai/gpt-5.5 -j 8

DELIBERATELY NOT TRUSTING breakdown.json's PATHS. The paths in there are
absolute and belong to the machine that generated the run ("/workspace/game/..."
for traces, that host's job dir for mp4s); on the judging box they point at
nothing. Demos are rediscovered from the directory tree instead, and
breakdown.json is read only for `build_ok`, which cannot be recovered any other
way once the sandbox is gone.

Results go to <trial>/verifier/rejudge/ so the stub's artifacts stay intact and
a re-run is always comparable against them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamecraft_bench.verifier.judges import JudgeError, get_judge          # noqa: E402
from gamecraft_bench.verifier.judges.base import JudgeRequest, RequirementSpec  # noqa: E402
from gamecraft_bench.verifier.score import (                               # noqa: E402
    _aggregate,
    _safe_eval_formula,
    _sample_frames,
    _validate_agg,
)

_MAX_ATTEMPTS = 3


def find_trials(root: Path) -> list[Path]:
    """Accepts a trial dir, a job dir, or an upload root holding several models.

    "Has a result.json" is NOT enough to identify a trial: a job directory has
    one too, and hf_upload.py carries it into the per-model directory. Only a
    trial's result.json names a trial_name, so that is the discriminator.
    """
    found: list[Path] = []
    for pattern in ("result.json", "*/result.json", "*/*/result.json"):
        for candidate in sorted(root.glob(pattern)):
            try:
                if "trial_name" in json.loads(candidate.read_text()):
                    found.append(candidate.parent)
            except (OSError, json.JSONDecodeError):
                continue
        if found:
            break
    return found


def load_rubric(trial: Path, tasks_dir: Path | None) -> tuple[dict, str]:
    """Prefer the rubric copied in beside the artifacts (hf_upload.py puts it
    there) so the judging machine needs no bench checkout at all."""
    local = trial / "verifier" / "rubric.json"
    if local.is_file():
        return json.loads(local.read_text()), "bundled"

    result = json.loads((trial / "result.json").read_text())
    task_path = (result.get("config", {}).get("task", {}) or {}).get("path", "")
    name = Path(task_path).name or Path(result.get("task_name", "")).name
    if not name:
        raise FileNotFoundError(f"{trial}: cannot tell which task this was")
    if tasks_dir is None:
        raise FileNotFoundError(
            f"{trial}: no bundled rubric and no --tasks-dir to look up {name!r}"
        )
    return json.loads((tasks_dir / name / "tests" / "rubric.json").read_text()), name


def demo_durations(trial: Path) -> dict[str, float]:
    """Recorded lengths, needed to re-derive frames. Written by the sweep."""
    bd = trial / "verifier" / "breakdown.json"
    try:
        return {d["demo_id"]: float(d.get("duration_seconds") or 0.0)
                for d in json.loads(bd.read_text()).get("demos", [])}
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return {}


def discover_demos(trial: Path, rubric: dict) -> list[tuple[str, Path, list[Path]]]:
    """Frames, sampling them out of the mp4 when the snapshot did not carry them.

    Frames are 95% of a trial's bytes (204 PNGs at ~265 KB against 2.2 MB of
    mp4), and they are not primary data -- _sample_frames derives them from the
    recording deterministically, seeded on demo_id. Shipping only the mp4 turns
    a 23 GB / 92k-file upload into roughly 1 GB and 4k files, and this end
    reconstructs the identical set. The only new requirement on the judging
    machine is ffmpeg; it still needs no Godot and no Xvfb.
    """
    demos_dir = trial / "verifier" / "demos"
    durations = demo_durations(trial)
    max_window = float(rubric.get("max_demo_seconds", 20.0))
    out = []
    for d in sorted(p for p in demos_dir.glob("*") if p.is_dir()):
        mp4 = d / f"{d.name}.mp4"
        frames = sorted((d / "frames").glob("*.png"))
        if not frames and mp4.is_file():
            frames = _sample_frames(
                mp4, d / "frames",
                duration_seconds=durations.get(d.name, 0.0),
                interval_seconds=0.5,
                max_window_seconds=max_window,
                seed=d.name,
            )
        if mp4.is_file() or frames:
            out.append((d.name, mp4, frames))
    return out


def build_ok_of(trial: Path) -> bool | None:
    """None means unknown -- the stub run never wrote a breakdown."""
    bd = trial / "verifier" / "breakdown.json"
    if not bd.is_file():
        return None
    try:
        return bool(json.loads(bd.read_text()).get("build_ok"))
    except json.JSONDecodeError:
        return None


def judge_trial(trial: Path, tasks_dir: Path | None, backend: str | None,
                model: str | None) -> dict:
    rubric, _ = load_rubric(trial, tasks_dir)
    requirements = rubric["requirements"]
    build_id = rubric["build_check"].get("id", "BUILD")

    build_ok = build_ok_of(trial)
    if build_ok is None:
        return {"trial": trial.name, "error": "no breakdown.json -- build result unknown"}

    per_req: dict[str, dict[str, float]] = {r["id"]: {} for r in requirements}
    judge_log: list[dict] = []
    errors: list[str] = []

    if build_ok:
        judge = get_judge(backend=backend, model=model)
        specs = [RequirementSpec(id=r["id"], description=r["description"])
                 for r in requirements]
        for demo_id, mp4, frames in discover_demos(trial, rubric):
            req = JudgeRequest(demo_id=demo_id, video_path=mp4,
                               frame_paths=frames, requirements=specs)
            t0, last = time.time(), None
            scores: dict = {}
            rationales: dict = {}
            for attempt in range(_MAX_ATTEMPTS):
                if attempt:
                    time.sleep(5 * attempt)
                try:
                    resp = judge.score(req)
                    scores, rationales, last = resp.scores, resp.rationales, None
                    break
                except JudgeError as e:
                    last = e
            if last is not None:
                errors.append(f"judge failed on {demo_id}: {last}")
            latency = time.time() - t0
            for r in requirements:
                rid = r["id"]
                try:
                    s = max(0.0, min(1.0, float(scores.get(rid, 0.0))))
                except (TypeError, ValueError):
                    s = 0.0
                per_req[rid][demo_id] = s
                judge_log.append({"demo_id": demo_id, "requirement_id": rid,
                                  "score": s, "rationale": rationales.get(rid, ""),
                                  "latency_seconds": round(latency, 3)})
    else:
        errors.append("build_check failed during generation; every requirement is 0")

    variables = {build_id: 1.0 if build_ok else 0.0}
    for r in requirements:
        variables[r["id"]] = _aggregate(_validate_agg(r), per_req[r["id"]])
    reward = _safe_eval_formula(rubric["score_formula"], variables)
    reward = max(0.0, min(1.0, reward))

    out = trial / "verifier" / "rejudge"
    out.mkdir(parents=True, exist_ok=True)
    (out / "reward.txt").write_text(f"{reward:.6f}\n")
    (out / "breakdown.json").write_text(json.dumps({
        "reward": reward,
        "formula": rubric["score_formula"],
        "build_ok": build_ok,
        "judge": {"backend": backend or os.environ.get("GAMECRAFT_BENCH_JUDGE", "openai"),
                  "model": model or os.environ.get("GAMECRAFT_BENCH_JUDGE_MODEL", "")},
        "variables": variables,
        "per_requirement": per_req,
        "errors": errors,
    }, indent=2))
    (out / "judge_log.json").write_text(json.dumps(judge_log, indent=2))
    return {"trial": trial.name, "reward": reward, "build_ok": build_ok,
            "demos": len({e["demo_id"] for e in judge_log}), "errors": errors}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, help="Job directory, or one trial directory.")
    ap.add_argument("--tasks-dir", type=Path, default=None,
                    help="Fallback rubric source (a bench checkout's tasks/).")
    ap.add_argument("--judge", default=None, help="Backend, e.g. openai.")
    ap.add_argument("--judge-model", default=None, help="e.g. openai/gpt-5.5")
    ap.add_argument("-j", "--jobs", type=int, default=4,
                    help="Trials judged in parallel (each is API-bound).")
    ap.add_argument("--skip-done", action="store_true",
                    help="Leave trials that already have verifier/rejudge/reward.txt.")
    args = ap.parse_args()

    trials = find_trials(args.root)
    if args.skip_done:
        trials = [t for t in trials
                  if not (t / "verifier" / "rejudge" / "reward.txt").is_file()]
    if not trials:
        print("nothing to judge")
        return 0
    print(f"judging {len(trials)} trial(s) with {args.jobs} in flight", flush=True)

    rows = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futs = {pool.submit(judge_trial, t, args.tasks_dir, args.judge,
                            args.judge_model): t for t in trials}
        for fut in futs:
            t = futs[fut]
            try:
                row = fut.result()
            except Exception as e:                       # noqa: BLE001
                row = {"trial": t.name, "error": f"{type(e).__name__}: {e}"}
            rows.append(row)
            print(f"  {row.get('trial'):<48} "
                  f"{'reward=%.4f' % row['reward'] if 'reward' in row else row.get('error')}",
                  flush=True)

    scored = [r["reward"] for r in rows if "reward" in r]
    if scored:
        print(f"\nmean reward: {sum(scored)/len(scored):.4f} over {len(scored)} trial(s)")
    failed = [r for r in rows if "error" in r]
    if failed:
        print(f"{len(failed)} trial(s) could not be judged")
    (args.root / "rejudge_summary.json").write_text(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
