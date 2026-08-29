#!/usr/bin/env python3
"""One tick of watch duty. Speaks only when something needs a decision.

State carries between ticks in a JSON file, so each tick is a comparison rather
than a re-derivation. The failure worth catching is not a crash -- it is money
leaving the account while nothing finishes, which is what two mass-kill batches
looked like: 24 trials, $47, zero artifacts, and nobody watching.
"""
import json, os, subprocess, sys, time
from pathlib import Path

# Import the classifier by path rather than as a package: making `scripts` one
# would mean dropping an __init__.py into the repo just to satisfy this watcher.
sys.path.insert(0, "/home/admin/wenyi/gamecraft-bench/scripts")
from sweep_state import classify, all_tasks                    # noqa: E402
from vitals import vitals, verdict, confirmed_dead             # noqa: E402

STATE = Path("/home/admin/wenyi/logs_vllm/.watch_state.json")
JOBS_DIR = "/home/admin/wenyi/gamecraft-bench-jobs"
PREFIX = "qwen3.8-27b-r"
BURN_ALERT = 8.0        # dollars in one tick that produced nothing
STALL_MIN = 35.0        # a workspace quiet this long is worth looking at


def _key() -> str:
    """Read the key from .env rather than trusting the caller's environment.

    The Monitor invokes this script directly, without sourcing anything, so
    os.environ was empty and every balance lookup silently returned None --
    printing "余额 ?" and, worse, disarming the credit-exhaustion alarm that
    is the whole point of watching.
    """
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    try:
        for line in Path("/home/admin/wenyi/.env").read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip() == "OPENROUTER_API_KEY":
                return v.strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def credits():
    import urllib.request
    key = _key()
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/credits",
                                     headers={"Authorization": f"Bearer {key}"})
        d = json.load(urllib.request.urlopen(req, timeout=20))["data"]
        return float(d["total_usage"]), float(d["total_credits"]) - float(d["total_usage"])
    except Exception:
        return None, None


def working(minutes: float = 8.0) -> int:
    """Trials whose rollout grew recently -- the only per-trial proof of work.

    codex appends to its rollout on every turn, so a fresh mtime means that
    agent is still doing something. The workspace is not a substitute: a model
    thinking for fifteen minutes writes no files, and the API log cannot be
    attributed to a trial at all.
    """
    now = time.time()
    n = 0
    for env in Path("/tmp/gamecraft-bench-sandboxes").glob("*__env"):
        newest = 0.0
        for r in env.rglob("rollout-*.jsonl"):
            try:
                newest = max(newest, r.stat().st_mtime)
            except OSError:
                continue
        if newest and (now - newest) / 60 < minutes:
            n += 1
    return n


def agents():
    try:
        out = subprocess.run(["pgrep", "-fc", "codex exec"], capture_output=True,
                             text=True, timeout=10).stdout.strip()
        return int(out or 0)
    except Exception:
        return -1


def main() -> int:
    prev = {}
    if STATE.exists():
        try:
            prev = json.loads(STATE.read_text())
        except Exception:
            prev = {}

    best = classify(PREFIX)
    done = sum(1 for v in best.values() if v[0] == "done")
    replay = sum(1 for v in best.values() if v[0] == "needs_replay")
    retry = sum(1 for v in best.values() if v[0] == "retry")
    # Only an outside kill counts toward the mass-kill alarm. CancelledError is
    # always our own hand -- stopping a round to change something raised retry
    # by twelve and rang the alarm, and an alarm that cries wolf for our own
    # deliberate actions is one we will learn to ignore before it matters.
    killed = sum(1 for v in best.values()
                 if v[0] == "retry" and v[1] == "NonZeroAgentExitCodeError")
    total = len(all_tasks())
    spend, left = credits()
    n = agents()
    tick = prev.get("tick", 0) + 1

    out = []
    # A round that has stopped producing agents is a round that has ended.
    if n == 0 and prev.get("agents", 1) > 0:
        out.append(f"轮次结束: done={done} 需补回放={replay} 需重跑={retry} / {total}"
                   f" — 该起下一轮了")
    # The killer coming back looks like a step change in outside kills.
    if killed - prev.get("killed", killed) >= 4:
        out.append(f"批量猝死: 被外部杀 {prev.get('killed')} -> {killed}"
                   f"（CancelledError 不计，那是我们自己停的）")
    # Paying without finishing anything.
    busy = working()
    if spend and prev.get("spend"):
        burn = spend - prev["spend"]
        # "Nothing finished" is not waste: every trial in a round takes up to
        # the benchmark's two hours, so the first two hours legitimately show
        # zero completions and a five-figure token bill. Waste is money moving
        # while no agent is doing anything -- no rollout has grown.
        if burn > BURN_ALERT and busy == 0:
            out.append(f"烧了 ${burn:.2f} 但 0/{n} 个 agent 在动（rollout 全无追加）"
                       f" — done={done} retry={retry}")
    if left is None:
        out.append("余额查不到 — 余额告警此刻是失效的，先修这个再谈别的")
    else:
        for t in (400, 250, 150, 80, 40, 15):
            if left <= t < (prev.get("left") or 1e9):
                out.append(f"余额剩 ${left:.0f}（done {done}/{total}）")
                break
    # A verdict, not a signal. The heartbeat used to print idle minutes and left
    # the reading to whoever saw it, and every misread this run came from that:
    # a backoff window looked like a stall, a canary that had finished its sleep
    # looked like a kill. Three layers decide now, and a trial is only called
    # dead after two SUSPECT samples at least three minutes apart -- longer than
    # the 300s backoff that would otherwise be mistaken for a stop.
    verdicts: dict[str, str] = {}
    samples: dict[str, dict] = {}
    prev_samples = prev.get("samples") or {}
    for job in Path(JOBS_DIR).glob(f"{PREFIX}*"):
        for cfg in job.glob("*/config.json"):
            trial = cfg.parent
            if (trial / "result.json").exists():
                continue
            v = vitals(trial)
            samples[trial.name] = v
            verdicts[trial.name] = verdict(v)
            if confirmed_dead(prev_samples.get(trial.name), v):
                out.append(f"判定真死（三层证据 × 两次采样）: {trial.name}"
                           f" — API静默{v['api_idle_min']:.0f}分"
                           f" 产物静默{v['artifact_idle_min']:.0f}分 树CPU 0")
    n_susp = sum(1 for x in verdicts.values() if x == "SUSPECT")
    n_gone = sum(1 for x in verdicts.values() if x == "GONE")
    n_ok = sum(1 for x in verdicts.values() if x == "HEALTHY")
    if n_susp > prev.get("suspect", 0):
        out.append(f"{n_susp} 个 trial 转 SUSPECT（三层皆静默），等第二次采样确认")

    for line in out:
        print(line, flush=True)
    if not out and tick % 2 == 0:
        bal = f"${left:.0f}" if left is not None else "?"
        print(f"进度 done={done} 补回放={replay} 重跑={retry}"
              f"(其中外部杀 {killed}) / {total} | 在飞判决 "
              f"HEALTHY={n_ok} SUSPECT={n_susp} GONE={n_gone} | 余额 {bal}",
              flush=True)

    STATE.write_text(json.dumps({"tick": tick, "done": done, "retry": retry,
                                 "killed": killed,
                                 "spend": spend, "left": left, "agents": n,
                                 "suspect": n_susp, "samples": samples, "busy": busy,
                                 "at": time.time()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
