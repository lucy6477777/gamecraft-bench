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
from sweep_state import classify, stalled, all_tasks           # noqa: E402

STATE = Path("/home/admin/wenyi/logs_vllm/.watch_state.json")
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
    if spend and prev.get("spend"):
        burn = spend - prev["spend"]
        made = done - prev.get("done", done)
        if burn > BURN_ALERT and made == 0:
            out.append(f"烧了 ${burn:.2f} 但零完成 — done={done} retry={retry} 在飞={n}")
    if left is None:
        out.append("余额查不到 — 余额告警此刻是失效的，先修这个再谈别的")
    else:
        for t in (400, 250, 150, 80, 40, 15):
            if left <= t < (prev.get("left") or 1e9):
                out.append(f"余额剩 ${left:.0f}（done {done}/{total}）")
                break
    # Quiet workspaces are reported, never acted on here: a long think between
    # tool calls writes nothing, and killing that would be killing progress.
    quiet = stalled(PREFIX, STALL_MIN)
    if len(quiet) > prev.get("quiet", 0) and quiet:
        out.append(f"{len(quiet)} 个 trial 工作区静默 >{STALL_MIN:.0f} 分钟: "
                   + ", ".join(f"{a}({b}m)" for a, b in quiet[:3]) + " — 待人工鉴别死活")

    for line in out:
        print(line, flush=True)
    if not out and tick % 2 == 0:
        bal = f"${left:.0f}" if left is not None else "?"
        print(f"进度 done={done} 补回放={replay} 重跑={retry}"
              f"(其中外部杀 {killed}) / {total} | 在飞 {n} | 余额 {bal}",
              flush=True)

    STATE.write_text(json.dumps({"tick": tick, "done": done, "retry": retry,
                                 "killed": killed,
                                 "spend": spend, "left": left, "agents": n,
                                 "quiet": len(quiet), "at": time.time()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
