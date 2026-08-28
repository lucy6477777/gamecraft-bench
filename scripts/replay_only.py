#!/usr/bin/env python3
"""Rebuild a trial's verifier artifacts without paying for generation again.

Generation is the expensive half; replay is free and depends on this host's
Godot/Xvfb/ffmpeg being right. When the replay half fails for an environment
reason -- the way conda's ffmpeg, built without x11grab, silently produced zero
frames for every demo -- the games are still there and only the recording needs
redoing. Re-running the sweep to recover them would be paying twice for the same
tokens.

    ./replay_only.py ../gamecraft-bench-jobs/or-pilot-glm-flash

Reuses score_project, so the build check, the Xvfb replay, the frame sampling
and the artifact layout are the same code the sweep runs -- not a reimplementation
that can drift from it. The judge is forced to the stub: this restores artifacts,
it does not score anything.

ONE REWRITE IS NEEDED. rubric.build_check.cmd is written for inside the sandbox
("godot --headless --path /workspace/game --quit-after 5") and runs through
`shell=True` with no cwd, so out here it would point at nothing and every trial
would come back build_ok=False. The sandbox path is repointed at the trial's own
host-backed workspace copy.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamecraft_bench.verifier.judges.stub import StubJudge   # noqa: E402
from gamecraft_bench.verifier.score import score_project      # noqa: E402

SANDBOX_PROJECT = "/workspace/game"


def find_trials(root: Path) -> list[Path]:
    found = []
    for pattern in ("result.json", "*/result.json", "*/*/result.json"):
        for c in sorted(root.glob(pattern)):
            try:
                if "trial_name" in json.loads(c.read_text()):
                    found.append(c.parent)
            except (OSError, json.JSONDecodeError):
                continue
        if found:
            break
    return found


def task_name_of(trial: Path) -> str | None:
    try:
        r = json.loads((trial / "result.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None
    p = (r.get("config", {}).get("task", {}) or {}).get("path", "")
    return Path(p).name or Path(r.get("task_name", "")).name or None


def check_ffmpeg() -> None:
    """The failure this script exists to repair is silent; refuse to repeat it."""
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-devices"],
                             capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError) as e:
        raise SystemExit(f"replay_only: cannot run ffmpeg: {e}")
    if "x11grab" not in out:
        raise SystemExit(
            "replay_only: this ffmpeg has no x11grab, so every replay would\n"
            "             produce nothing. Put one that does first on PATH\n"
            "             (/usr/bin/ffmpeg on this host)."
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--tasks-dir", type=Path,
                    default=Path(__file__).resolve().parents[1] / "tasks")
    ap.add_argument("--keep", action="store_true",
                    help="Move the existing verifier/ aside instead of overwriting.")
    args = ap.parse_args()

    check_ffmpeg()

    trials = find_trials(args.root)
    if not trials:
        print(f"no trials under {args.root}")
        return 1
    print(f"re-replaying {len(trials)} trial(s)")

    rc = 0
    for trial in trials:
        project = trial / "sandbox" / "workspace" / "game"
        if not project.is_dir():
            print(f"  {trial.name}: no generated project, skipping")
            continue
        name = task_name_of(trial)
        rubric_src = (trial / "verifier" / "rubric.json")
        if not rubric_src.is_file():
            rubric_src = args.tasks_dir / (name or "") / "tests" / "rubric.json"
        if not rubric_src.is_file():
            print(f"  {trial.name}: no rubric for task {name!r}, skipping")
            rc = 1
            continue

        rubric = json.loads(rubric_src.read_text())
        rubric["build_check"]["cmd"] = rubric["build_check"]["cmd"].replace(
            SANDBOX_PROJECT, str(project.resolve()))

        out_dir = trial / "verifier"
        if args.keep and out_dir.exists():
            shutil.move(str(out_dir), str(trial / "verifier.stub"))
        out_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(rubric, fh)
            tmp_rubric = Path(fh.name)
        try:
            result = score_project(
                project_dir=project.resolve(),
                rubric_path=tmp_rubric,
                output_dir=out_dir.resolve(),
                judge=StubJudge(model="0"),
            )
        finally:
            tmp_rubric.unlink(missing_ok=True)

        frames = len(list((out_dir / "demos").rglob("*.png")))
        mp4s = len(list((out_dir / "demos").rglob("*.mp4")))
        print(f"  {trial.name}: build_ok={result.build_ok} "
              f"demos={len(result.demos)} mp4={mp4s} frames={frames}")
        for err in result.errors[:3]:
            print(f"      ! {err}")
            rc = 1
        # The rubric belongs beside the artifacts so rejudge.py stays self-contained.
        shutil.copy2(rubric_src, out_dir / "rubric.json")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
