#!/usr/bin/env python3
"""One line for three sweeps. Verdicts, not signals."""
import json, os, subprocess, sys, time, urllib.request
sys.path.insert(0, "/home/admin/wenyi/gamecraft-bench/scripts")
from sweep_state import classify, all_tasks
from vitals import vitals_batch, verdict
from pathlib import Path

JOBS = Path("/home/admin/wenyi/gamecraft-bench-jobs")
MODELS = [("qwen", "qwen3.8-27b-r", "qwen3.8-27b-r"),
          ("kimi", "kimi-k2.6-r", "kimi-k2.6"),
          ("glm",  "glm-5.3-flash-r", "glm-5.3-flash")]
STATE = Path("/home/admin/wenyi/logs_vllm/.watch3.json")


def key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if k: return k
    for line in Path("/home/admin/wenyi/.env").read_text().splitlines():
        a, _, b = line.partition("=")
        if a.strip() == "OPENROUTER_API_KEY": return b.strip().strip('"')
    return ""


def bal():
    try:
        r = urllib.request.Request("https://openrouter.ai/api/v1/credits",
                                   headers={"Authorization": f"Bearer {key()}"})
        d = json.load(urllib.request.urlopen(r, timeout=20))["data"]
        return d["total_credits"] - d["total_usage"]
    except Exception:
        return None


prev = {}
if STATE.exists():
    try: prev = json.loads(STATE.read_text())
    except Exception: pass

FRESH_MIN = 10.0          # one tick: a mass kill lands inside a single window
MASS_DEATHS = 6           # glm sheds 2-4 per twenty minutes to bugs already
                          # diagnosed and already fixed pending a round
                          # boundary. That is a known cost, not news. What is
                          # worth waking for is the other shape: a dozen
                          # trials dying in the same instant.


def _age_min(trial) -> float:
    """Minutes since this attempt's result was written."""
    try:
        return (time.time() - (trial / "result.json").stat().st_mtime) / 60
    except OSError:
        return 1e9


total = len(all_tasks())
out, now = [], {}
harbor = subprocess.run(["pgrep", "-af", "harbor run"], capture_output=True, text=True).stdout
parts = []
for tag, rnd, cls in MODELS:
    best = classify(cls)
    done = sum(1 for v in best.values() if v[0] == "done")
    # Count failures by when they happened, not how many exist. The old
    # cumulative count jumped by thirteen the moment classify started
    # reporting r4's reason instead of r3's -- same thirteen failures, an
    # hour old, reported as a mass death in progress. A window cannot be
    # moved by a change in how the past is labelled.
    killed = sum(1 for v in best.values()
                 if v[0] == "retry" and v[1] == "NonZeroAgentExitCodeError"
                 and _age_min(v[2]) <= FRESH_MIN)
    up = any(f"--job-name {rnd}" in ln for ln in harbor.splitlines())
    live = [cfg.parent for job in JOBS.glob(f"{rnd}*")
            for cfg in job.glob("*/config.json")
            if not (cfg.parent / "result.json").exists()]
    vs = [verdict(v) for v in vitals_batch(live).values()] if live else []
    ok = vs.count("HEALTHY"); sus = vs.count("SUSPECT")
    now[f"{tag}_done"] = done; now[f"{tag}_killed"] = killed; now[f"{tag}_up"] = up
    if killed >= MASS_DEATHS:
        out.append(f"{tag} 批量猝死: {FRESH_MIN:.0f} 分钟内 {killed} 个 agent 非正常退出")
    if not up and prev.get(f"{tag}_up", True):
        out.append(f"{tag} 轮次结束（harbor 退出）: done={done}/{total}")
    if sus:
        out.append(f"{tag} {sus} 个 SUSPECT（三层皆静默）")
    parts.append(f"{tag} {done}/{total}(飞{ok})")

b = bal()
now["tick"] = prev.get("tick", 0) + 1
now["left"] = b
if b is not None:
    for t in (800, 500, 300, 150, 80, 40):
        if b <= t < (prev.get("left") or 1e9):
            out.append(f"余额剩 ${b:.0f}"); break
for line in out: print(line, flush=True)
if not out and now["tick"] % 2 == 0:
    print(" | ".join(parts) + f" | 余额 ${b:.0f}" if b else " | ".join(parts), flush=True)
STATE.write_text(json.dumps(now))
