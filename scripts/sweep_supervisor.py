#!/usr/bin/env python3
"""Start the next round when harbor stops with work still to do.

One harbor process owns every in-flight trial, so when something SIGTERMs it --
which happened once at 65/140, taking twelve trials and 806 minutes of agent
time with it -- the round simply ends and nothing notices until a human looks.
The trials that were in flight are gone either way; what this saves is the wait.
Rounds were being restarted by hand on a 20-minute check, so up to 20 minutes of
twelve-way concurrency sat idle after every death.

It will not start a round it cannot pay for. A batch of N trials that runs out
of credit halfway leaves N unscoreable half-games and spends the money anyway,
so the floor is a whole batch's worth plus a margin; below that it stops and
says so rather than reaching for the last dollars.

    ./sweep_supervisor.py --concurrency 12 --floor 90
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
JOBS = REPO.parent / "gamecraft-bench-jobs"
LOGS = REPO.parent / "logs_vllm"
sys.path.insert(0, str(REPO / "scripts"))
from sweep_state import all_tasks, classify            # noqa: E402


def harbor_alive(prefix: str) -> bool:
    """Only OUR harbor. A global match sees somebody else's sweep and sits idle
    believing ours is still running -- and the watchdog that outlives its own
    task is the one that starts a round on top of a name already in use."""
    r = subprocess.run(["pgrep", "-af", "harbor run"], capture_output=True, text=True)
    return any(f"--job-name {prefix}" in ln or f"--job-name={prefix}" in ln
               for ln in (r.stdout or "").splitlines())


def balance() -> float | None:
    key = os.environ.get("OPENROUTER_API_KEY") or _key_from_env_file()
    if not key:
        return None
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/credits",
                                     headers={"Authorization": f"Bearer {key}"})
        d = json.load(urllib.request.urlopen(req, timeout=20))["data"]
        return float(d["total_credits"]) - float(d["total_usage"])
    except Exception:
        return None


def _key_from_env_file() -> str:
    try:
        for line in (REPO.parent / ".env").read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip() == "OPENROUTER_API_KEY":
                return v.strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def own_cost_per_trial(prefix: str = "qwen3.8-27b-r") -> float:
    """Our spend per trial, from our own token counts -- not from the balance.

    The OpenRouter key is shared with other people, so the movement in
    total_usage is partly theirs; pricing the floor off it means their traffic
    decides when our sweep stops. harbor counts our tokens off the codex
    rollouts, and list price turns that into dollars that are only ours.
    """
    IN, OUT = 4.25e-7, 2.55e-6          # qwen3.8-27b list price per token
    tok_in = tok_out = 0
    trials = 0
    for res in Path(JOBS).glob(f"{prefix}*/result.json"):
        try:
            st = json.loads(res.read_text()).get("stats") or {}
        except (OSError, json.JSONDecodeError):
            continue
        tok_in += st.get("n_input_tokens") or 0
        tok_out += st.get("n_output_tokens") or 0
        trials += st.get("n_completed_trials") or 0
    if not trials:
        return 5.88
    return (tok_in * IN + tok_out * OUT) / trials


def remaining(prefix: str) -> list[str]:
    best = classify(prefix)
    todo = [t for t, v in best.items() if v[0] == "retry"]
    todo += sorted(all_tasks() - set(best))
    return sorted(set(todo))


def next_round_number(prefix: str) -> int:
    n = 0
    for p in JOBS.glob(f"{prefix}*"):
        m = re.fullmatch(re.escape(prefix) + r"(\d+)", p.name)
        if m:
            n = max(n, int(m.group(1)))
    return n + 1


def start_round(tasks: list[str], rnd: int, concurrency: int, prefix: str) -> None:
    args = " ".join(f'-i "{t}"' for t in tasks)
    job = f"{prefix}{rnd}"
    log = LOGS / f"sweep_qwen_r{rnd}.log"
    cmd = (f'cd {REPO} && ./scripts/run_openrouter.sh qwen38-27b -p tasks {args} '
           f'-n {concurrency} --job-name {job} > {log} 2>&1')
    subprocess.Popen(["setsid", "bash", "-c", cmd],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[{time.strftime('%H:%M:%S')}] 起 {job}: {len(tasks)} 题, -n {concurrency}, 日志 {log}",
          flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="qwen3.8-27b-r")
    ap.add_argument("--concurrency", type=int, default=12)
    ap.add_argument("--per-task", type=float, default=None,
                    help="Dollars per finished trial. Measured from our own "
                         "token ledger when omitted -- the account balance is "
                         "shared with other people, so a credits diff prices "
                         "their traffic into our floor.")
    ap.add_argument("--floor-margin", type=float, default=20.0)
    ap.add_argument("--poll", type=int, default=60)
    ap.add_argument("--max-rounds", type=int, default=12,
                    help="Refuse to spin forever if rounds keep dying instantly.")
    args = ap.parse_args()

    per_task = args.per_task if args.per_task is not None else own_cost_per_trial()
    floor = args.concurrency * per_task + args.floor_margin
    print(f"supervisor: 每轮门槛 ${floor:.0f}（{args.concurrency} × ${per_task:.2f}/题"
          f" + ${args.floor_margin} 余量；单价来自自家 token 账本）",
          flush=True)
    started = 0

    while True:
        if harbor_alive(args.prefix):
            time.sleep(args.poll)
            continue

        todo = remaining(args.prefix)
        if not todo:
            print(f"[{time.strftime('%H:%M:%S')}] 140 题全部有结果，supervisor 退出", flush=True)
            return 0

        bal = balance()
        if bal is None:
            print(f"[{time.strftime('%H:%M:%S')}] 查不到余额，不敢开新轮，退出", flush=True)
            return 1
        if bal < floor:
            print(f"[{time.strftime('%H:%M:%S')}] 余额 ${bal:.2f} < 门槛 ${floor:.0f}，"
                  f"剩 {len(todo)} 题不跑了 — 开一批跑不完的批次只会留下半截产物",
                  flush=True)
            return 0
        if started >= args.max_rounds:
            print(f"[{time.strftime('%H:%M:%S')}] 已连开 {started} 轮，停下等人看一眼", flush=True)
            return 1

        rnd = next_round_number(args.prefix)
        print(f"[{time.strftime('%H:%M:%S')}] harbor 不在了，剩 {len(todo)} 题，余额 ${bal:.2f}",
              flush=True)
        start_round(todo, rnd, args.concurrency, args.prefix)
        started += 1
        time.sleep(90)          # 给 harbor 起身的时间，免得判成"还没起来"又开一轮


if __name__ == "__main__":
    raise SystemExit(main())
