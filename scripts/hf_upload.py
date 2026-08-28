#!/usr/bin/env python3
"""Publish generation-only job dirs to a HuggingFace dataset repo.

The judging machine gets everything it needs from this snapshot and nothing it
does not: no Godot, no Xvfb, no bench checkout. Each trial carries its own
rubric.json (copied in here) so scripts/rejudge.py is self-contained.

    ./hf_upload.py --repo WenyiWU0111/gamecraft-bench-baselines \
        qwen3.8-27b=../gamecraft-bench-jobs/qwen38-full \
        kimi-k2.6=../gamecraft-bench-jobs/kimi-full

STAGED WITH HARDLINKS, NOT COPIES. A full sweep is ~6 GB across ~50k files
(103 sampled frames per trial is most of that count), and upload_large_folder --
the only uploader that chunks, resumes and parallelises at that scale -- has no
path_in_repo, so the local tree has to be shaped like the repo first. Hardlinks
make that free; the fallback to copying is there for a staging dir someone put
on another filesystem.

Run with --dry-run first: it prints the file count and size, which is what
decides whether an upload is minutes or hours.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tarfile
from pathlib import Path

IGNORE = ["*.pyc", "__pycache__/*", ".DS_Store"]
# Sampled frames are 95% of the bytes and are derived, not primary: rejudge.py
# rebuilds the identical set from the mp4 (deterministic, seeded on demo_id).
FRAME_GLOB = "verifier/demos/*/frames/*.png"
# The generated Godot project is ~1,240 files but only ~5 MB -- 602 asset files
# copied out of the mounted library, plus the .godot import cache. Left loose it
# is the entire file-count problem (420 trials x 1,240 = half a million objects,
# five times what a HF repo should hold), while judging never opens it. Archived
# it is one object per trial and still fully recoverable.
GAME_SUBPATH = "sandbox/workspace/game"


def task_name_of(trial: Path) -> str | None:
    try:
        result = json.loads((trial / "result.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None
    path = (result.get("config", {}).get("task", {}) or {}).get("path", "")
    return Path(path).name or Path(result.get("task_name", "")).name or None


def link_tree(src: Path, dst: Path, skip_frames: bool = True,
              archive_game: bool = True) -> tuple[int, int]:
    """Hardlink src into dst, falling back to copy across filesystems."""
    files = bytes_ = 0
    drop = {p.resolve() for p in src.glob(FRAME_GLOB)} if skip_frames else set()
    game_dir = (src / GAME_SUBPATH).resolve()
    for s in src.rglob("*"):
        if s.is_symlink() or not s.is_file():
            continue
        if s.resolve() in drop:
            continue
        if archive_game and game_dir in s.resolve().parents:
            continue
        d = dst / s.relative_to(src)
        d.parent.mkdir(parents=True, exist_ok=True)
        if not d.exists():
            try:
                os.link(s, d)
            except OSError:
                shutil.copy2(s, d)
        files += 1
        bytes_ += s.stat().st_size

    if archive_game and game_dir.is_dir():
        tar_path = dst / "sandbox" / "game.tar.gz"
        tar_path.parent.mkdir(parents=True, exist_ok=True)
        if not tar_path.exists():
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(game_dir, arcname="game")
        files += 1
        bytes_ += tar_path.stat().st_size
    return files, bytes_


def stage(model_key: str, job_dir: Path, staging: Path, tasks_dir: Path,
          skip_frames: bool = True, archive_game: bool = True) -> tuple[int, int]:
    out = staging / model_key
    trials = sorted(p.parent for p in job_dir.glob("*/result.json"))
    if not trials:
        print(f"  {model_key}: no trials under {job_dir}", file=sys.stderr)
        return 0, 0

    files = bytes_ = 0
    missing_rubric = []
    for trial in trials:
        f, b = link_tree(trial, out / trial.name, skip_frames=skip_frames,
                         archive_game=archive_game)
        files += f
        bytes_ += b
        # The rubric is what rejudge scores against; without it the snapshot is
        # only replayable on a machine that has the bench checked out.
        name = task_name_of(trial)
        rubric = tasks_dir / name / "tests" / "rubric.json" if name else None
        if rubric and rubric.is_file():
            dest = out / trial.name / "verifier" / "rubric.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rubric, dest)
            files += 1
            bytes_ += rubric.stat().st_size
        else:
            missing_rubric.append(trial.name)

    # Job-level files (result.json, job.log) sit beside the trial dirs.
    for f_ in job_dir.glob("*"):
        if f_.is_file():
            d = out / f_.name
            if not d.exists():
                try:
                    os.link(f_, d)
                except OSError:
                    shutil.copy2(f_, d)
            files += 1
            bytes_ += f_.stat().st_size

    print(f"  {model_key}: {len(trials)} trials, {files:,} files, {bytes_/2**30:.2f} GiB")
    if missing_rubric:
        print(f"    WARNING no rubric bundled for {len(missing_rubric)} trial(s): "
              f"{', '.join(missing_rubric[:3])}{'...' if len(missing_rubric) > 3 else ''}")
    return files, bytes_


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pairs", nargs="+", metavar="MODEL_KEY=JOB_DIR")
    ap.add_argument("--repo", required=True, help="e.g. WenyiWU0111/gamecraft-bench-baselines")
    ap.add_argument("--tasks-dir", type=Path,
                    default=Path(__file__).resolve().parents[1] / "tasks")
    ap.add_argument("--staging", type=Path, default=None,
                    help="Defaults to <first job dir>/../.hf_staging (same "
                         "filesystem, so hardlinks work).")
    ap.add_argument("--private", action="store_true", default=True)
    ap.add_argument("--public", dest="private", action="store_false")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--with-frames", dest="skip_frames", action="store_false",
                    default=True,
                    help="Upload the sampled PNGs too. Off by default: they are "
                         "95%% of the bytes and rejudge.py re-derives them from "
                         "the mp4 with the same seed.")
    ap.add_argument("--loose-game", dest="archive_game", action="store_false",
                    default=True,
                    help="Upload the generated project as a file tree instead of "
                         "one game.tar.gz per trial. Blows up the object count.")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    jobs: list[tuple[str, Path]] = []
    for pair in args.pairs:
        if "=" not in pair:
            print(f"error: expected MODEL_KEY=JOB_DIR, got {pair!r}", file=sys.stderr)
            return 1
        k, _, v = pair.partition("=")
        jobs.append((k, Path(v).resolve()))

    staging = args.staging or (jobs[0][1].parent / ".hf_staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    print(f"staging -> {staging}")
    total_f = total_b = 0
    for key, job_dir in jobs:
        f, b = stage(key, job_dir, staging, args.tasks_dir, args.skip_frames,
                     args.archive_game)
        total_f += f
        total_b += b
    print(f"total: {total_f:,} files, {total_b/2**30:.2f} GiB")

    if args.dry_run:
        print("dry run -- nothing uploaded; staging left in place for inspection")
        return 0

    token = os.environ.get("HF_TOKEN")
    if not token:
        print("error: HF_TOKEN not set", file=sys.stderr)
        return 1

    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(args.repo, repo_type="dataset", private=args.private, exist_ok=True)
    print(f"uploading to dataset {args.repo} (private={args.private})")
    api.upload_large_folder(
        repo_id=args.repo,
        folder_path=str(staging),
        repo_type="dataset",
        ignore_patterns=IGNORE,
        num_workers=args.workers,
    )
    print(f"done: https://huggingface.co/datasets/{args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
