#!/usr/bin/env python3
"""What is finished, what must be re-generated, and what only needs a replay.

The distinction that saves the most money is between a trial that FAILED and a
trial that merely has no artifacts:

  done          a result exists and mp4s exist. Never run again.
  needs_replay  the agent finished (cleanly, or by exhausting the bench's own
                7200 s budget) but no recording came out -- the ffmpeg/x11grab
                class of problem. Re-running the agent would pay a second time
                for tokens already spent; scripts/replay_only.py rebuilds these
                for free.
  retry         an infrastructure failure: the process was killed from outside,
                we stopped it, or the provider rate-limited. Nothing was
                learned about the model, so the task must be generated again.
  pending       never attempted.

AgentTimeoutError counts as DONE, not as a failure. 7200 s is the benchmark's
own per-task budget, written in every task.toml; a model that runs out of it has
produced its answer for this benchmark, and re-running costs two more hours and
another $9 to arrive at the same verdict.

    ./sweep_state.py                       # human summary
    ./sweep_state.py --next-round-args     # the -i flags for the next round
    ./sweep_state.py --stalled             # trials whose workspace stopped growing
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
JOBS = REPO.parent / "gamecraft-bench-jobs"

# Exceptions that say nothing about the model, so the task must be re-generated.
INFRA = {
    "NonZeroAgentExitCodeError",   # SIGTERMed from outside the harness
    "CancelledError",              # we stopped the sweep
    "ApiRateLimitError",
    "ApiUsageLimitError",
    "UnknownApiError",
}
# Exceptions that ARE the result.
SCOREABLE = {None, "AgentTimeoutError"}


def all_tasks() -> set[str]:
    return {p.name for p in (REPO / "tasks").iterdir()
            if p.is_dir() and (p / "task.toml").is_file() and p.name != "example"}


def trial_rows(prefix: str):
    for job in sorted(JOBS.glob(f"{prefix}*")):
        if not job.is_dir():
            continue
        for res in sorted(job.glob("*/result.json")):
            try:
                d = json.loads(res.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            task = Path((d.get("config", {}).get("task", {}) or {}).get("path", "")).name
            if not task:
                continue
            exc = (d.get("exception_info") or {}).get("exception_type")
            trial = res.parent
            mp4 = len(list((trial / "verifier" / "demos").glob("*/*.mp4")))
            traces = len(list(
                (trial / "sandbox" / "workspace" / "game" / "demo_outputs").glob("*.json")))
            yield task, exc, mp4, traces, trial


def classify(prefix: str):
    best: dict[str, tuple[str, str | None, Path]] = {}
    order = {"done": 3, "needs_replay": 2, "retry": 1}
    for task, exc, mp4, traces, trial in trial_rows(prefix):
        if exc in SCOREABLE:
            # Three cases, and only the middle one is worth any work:
            #   recordings exist                -> finished
            #   traces but no recordings        -> replay can build them, free
            #   no traces at all                -> finished, and the score is 0
            # The last is not a failure to repair. The agent spent the whole
            # 7200 s the benchmark allows and never demonstrated its game;
            # BUILD * 0 is the answer, and running it again would be giving the
            # model a second budget that no other model on the board received.
            if mp4 > 0:
                state = "done"
            elif traces > 0:
                state = "needs_replay"
            else:
                state = "done"
        elif exc in INFRA:
            state = "retry"
        else:
            # An unfamiliar exception is the model's answer only if it left
            # something behind; otherwise treat it as worth one more attempt.
            state = "done" if mp4 > 0 else "retry"
        prev = best.get(task)
        # Best state wins, because a task finished in r2 must not be rerun
        # just because r4's attempt at it was killed. But on a tie the newer
        # attempt wins: with r3 and r4 both 'retry', glob order handed back
        # r3's CancelledError -- our own stop hours earlier -- and hid the
        # NonZeroAgentExitCodeError that r4 had just died of. The state was
        # right and the reason was stale, which is the worst of both: the
        # round plan looked correct while the diagnosis pointed at the wrong
        # failure, and twice I read 'qwen has no failures' off it.
        if (prev is None
                or order[state] > order[prev[0]]
                or (order[state] == order[prev[0]] and _mtime(trial) > _mtime(prev[2]))):
            best[task] = (state, exc, trial)
    return best


def _mtime(trial: Path) -> float:
    r = trial / "result.json"
    try:
        return r.stat().st_mtime
    except OSError:
        return 0.0


def stalled(prefix: str, minutes: float):
    """Trials whose generated project has stopped growing. Slow is not dead:
    a long think between tool calls writes nothing, so this only reports, and
    the caller confirms against CPU before killing anything."""
    now = time.time()
    out = []
    for job in sorted(JOBS.glob(f"{prefix}*")):
        for ws in job.glob("*/sandbox/workspace"):
            if (ws.parent.parent / "result.json").is_file():
                continue                      # already finished
            newest = 0.0
            for p in ws.rglob("*"):
                try:
                    newest = max(newest, p.stat().st_mtime)
                except OSError:
                    continue
            age = (now - newest) / 60 if newest else -1
            if age < 0 or age >= minutes:
                out.append((ws.parent.parent.name, round(age, 1)))
    return sorted(out, key=lambda r: -r[1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="qwen3.8-27b-r")
    ap.add_argument("--next-round-args", action="store_true")
    ap.add_argument("--stalled", type=float, metavar="MIN", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    tasks = all_tasks()
    best = classify(args.prefix)
    done = sorted(t for t, v in best.items() if v[0] == "done")
    replay = sorted(t for t, v in best.items() if v[0] == "needs_replay")
    retry = sorted(t for t, v in best.items() if v[0] == "retry")
    pending = sorted(tasks - set(best))

    if args.next_round_args:
        # Only what still needs the model: never re-generate a finished task.
        for t in retry + pending:
            print(f'-i "{t}"')
        return 0

    if args.stalled is not None:
        rows = stalled(args.prefix, args.stalled)
        if not rows:
            print("no trial has gone quiet")
        for name, age in rows:
            print(f"  {name}  workspace idle {age} min")
        return 0

    if args.json:
        print(json.dumps({"done": done, "needs_replay": replay,
                          "retry": retry, "pending": pending}, indent=1))
        return 0

    print(f"total tasks        : {len(tasks)}")
    print(f"done (scoreable)   : {len(done)}")
    print(f"needs replay (free): {len(replay)}"
          + (f"  -> {', '.join(replay[:4])}{'...' if len(replay) > 4 else ''}" if replay else ""))
    print(f"retry (re-generate): {len(retry)}"
          + (f"  -> {', '.join(retry[:4])}{'...' if len(retry) > 4 else ''}" if retry else ""))
    print(f"pending            : {len(pending)}")
    reasons: dict[str, int] = {}
    for t in retry:
        reasons[best[t][1] or "?"] = reasons.get(best[t][1] or "?", 0) + 1
    if reasons:
        print(f"retry reasons      : {reasons}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
