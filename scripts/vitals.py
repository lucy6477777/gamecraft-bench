#!/usr/bin/env python3
"""Is this trial alive? Three layers of evidence, and none of them alone.

Every wrong call made during this sweep came from reading one signal and acting
on it. The workspace goes quiet for forty minutes while the model thinks and
writes no files. The instantaneous %CPU of a process waiting on a socket is
0.0, always, alive or dead. A whole batch stops appending anything at once and
it is a backoff window, not a death.

So: an API layer, an artifact layer, and a process layer, and a verdict only
when all three agree -- twice, minutes apart, because a single sample cannot
tell a pause from a stop.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

SANDBOXES = Path("/tmp/gamecraft-bench-sandboxes")
CPU_WINDOW_SEC = 3.0


def _newest_mtime(root: Path, pattern: str = "*") -> float:
    newest = 0.0
    try:
        for p in root.rglob(pattern):
            try:
                if p.is_file():
                    newest = max(newest, p.stat().st_mtime)
            except OSError:
                continue
    except OSError:
        pass
    return newest


def _tree_pids(pid: int) -> list[int]:
    """Every descendant, not just the top process.

    A trial is bash -> unshare -> bash -> codex, and the parent sits in wait()
    burning nothing while the child works. Looking only at the top of the tree
    reports zero CPU for a perfectly busy trial.
    """
    out = [pid]
    try:
        r = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True,
                           text=True, timeout=5)
        for line in (r.stdout or "").split():
            out.extend(_tree_pids(int(line)))
    except (subprocess.SubprocessError, ValueError):
        pass
    return out


def _cpu_jiffies(pids: list[int]) -> int:
    total = 0
    for p in pids:
        try:
            parts = Path(f"/proc/{p}/stat").read_text().rsplit(") ", 1)[1].split()
            total += int(parts[11]) + int(parts[12])      # utime + stime
        except (OSError, IndexError, ValueError):
            continue
    return total


def find_trial_pid(trial_name: str) -> int | None:
    """The agent process for one trial, matched on its own argv."""
    try:
        r = subprocess.run(["pgrep", "-f", "codex exec"], capture_output=True,
                           text=True, timeout=10)
    except subprocess.SubprocessError:
        return None
    for line in (r.stdout or "").split():
        try:
            pid = int(line)
            cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(
                errors="replace")
        except (OSError, ValueError):
            continue
        if trial_name in cmd:
            return pid
    return None


def vitals(trial_dir: Path) -> dict:
    """One sample of the three layers. Minutes idle, and CPU actually consumed."""
    name = trial_dir.name
    now = time.time()

    env = SANDBOXES / f"{name}__env"
    api_m = _newest_mtime(env, "rollout-*.jsonl")
    art_m = _newest_mtime(trial_dir / "sandbox" / "workspace")

    pid = find_trial_pid(name)
    if pid is None:
        cpu = 0
        alive = False
    else:
        alive = True
        pids = _tree_pids(pid)
        a = _cpu_jiffies(pids)
        time.sleep(CPU_WINDOW_SEC)
        cpu = _cpu_jiffies(_tree_pids(pid)) - a

    return {
        "trial": name,
        "api_idle_min": (now - api_m) / 60 if api_m else -1.0,
        "artifact_idle_min": (now - art_m) / 60 if art_m else -1.0,
        "tree_cpu_jiffies": cpu,
        "process_alive": alive,
        "at": now,
    }


def verdict(v: dict, idle_min: float = 15.0) -> str:
    """HEALTHY / SUSPECT / GONE for a single sample.

    GONE only when no agent process exists at all -- that is not a judgement
    call. SUSPECT needs all three layers quiet at once; any one of them moving
    means something is still happening and the trial is left alone.
    """
    if not v["process_alive"]:
        return "GONE"
    quiet_api = v["api_idle_min"] < 0 or v["api_idle_min"] >= idle_min
    quiet_art = v["artifact_idle_min"] < 0 or v["artifact_idle_min"] >= idle_min
    no_cpu = v["tree_cpu_jiffies"] == 0
    return "SUSPECT" if (quiet_api and quiet_art and no_cpu) else "HEALTHY"


def confirmed_dead(prev: dict | None, cur: dict, min_gap_sec: float = 180.0,
                   idle_min: float = 15.0) -> bool:
    """Two SUSPECT samples, far enough apart to outlast a retry cycle.

    codex backs off up to 300s and the harness retries on its own schedule; a
    window shorter than one backoff period will read self-healing as death.
    """
    if verdict(cur, idle_min) != "SUSPECT":
        return False
    if not prev or verdict(prev, idle_min) != "SUSPECT":
        return False
    return (cur["at"] - prev["at"]) >= min_gap_sec
