#!/usr/bin/env python3
"""What a sweep cost, from the two sources on this route that actually report.

    ./or_cost.py --snapshot                       # before the sweep
    ./or_cost.py <job-dir>... --since 50396.0330  # after

WHY NOT PER-REQUEST. OpenRouter's /api/v1/generation?id=<gen> is the obvious
answer and it is empty here: for these models it returns provider_name but
tokens_prompt=0, total_cost=0 -- the upstream never reports usage back for the
Responses-API path. Verified across 88 generations from a completed run, and
re-checked 15 minutes later in case it was settling. It is not.

So cost comes from /api/v1/credits, whose total_usage is authoritative and
account-wide -- hence the snapshot-and-diff. Per-model attribution comes from
harbor's own accounting in result.json (stats.n_*_tokens, counted off the codex
rollout), priced against OpenRouter's list. That estimate ignores any cache
discount the provider applies, so it is an upper bound; the credits diff is the
number that was really charged.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

CREDITS = "https://openrouter.ai/api/v1/credits"
MODELS = "https://openrouter.ai/api/v1/models"


def api(url: str, key: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as fh:
        return json.load(fh)


def total_usage(key: str) -> float:
    return float(api(CREDITS, key)["data"]["total_usage"])


def pricing(key: str) -> dict[str, tuple[float, float]]:
    return {m["id"]: (float(m["pricing"]["prompt"]), float(m["pricing"]["completion"]))
            for m in api(MODELS, key)["data"]}


def model_of(job_dir: Path) -> str | None:
    """The model harbor was given, read off the first trial's config."""
    for c in sorted(job_dir.glob("*/config.json")):
        try:
            cfg = json.loads(c.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        agent = cfg.get("agent") or {}
        if isinstance(agent, dict):
            # harbor writes it as agent.model_name; the flat keys are older shapes.
            for k in ("model_name", "model"):
                if isinstance(agent.get(k), str):
                    return agent[k]
        for k in ("model", "model_name"):
            if isinstance(cfg.get(k), str):
                return cfg[k]
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs", nargs="*", type=Path)
    ap.add_argument("--snapshot", action="store_true",
                    help="Print account total_usage and exit. Record it before a sweep.")
    ap.add_argument("--since", type=float, default=None,
                    help="A total_usage from an earlier --snapshot; prints the diff.")
    ap.add_argument("--extrapolate-to", type=int, default=140)
    args = ap.parse_args()

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        print("error: OPENROUTER_API_KEY not set")
        return 1

    now = total_usage(key)
    if args.snapshot:
        print(f"{now:.4f}")
        return 0

    print(f"account total_usage now : ${now:,.4f}")
    if args.since is not None:
        print(f"charged since snapshot  : ${now - args.since:,.4f}   <-- what was really billed")

    prices = pricing(key)
    for job in args.jobs:
        result = job / "result.json"
        if not result.is_file():
            print(f"\n{job}: no result.json")
            continue
        stats = json.loads(result.read_text()).get("stats") or {}
        n_in = stats.get("n_input_tokens") or 0
        n_cache = stats.get("n_cache_tokens") or 0
        n_out = stats.get("n_output_tokens") or 0
        trials = stats.get("n_completed_trials") or 0
        errored = stats.get("n_errored_trials") or 0

        model = model_of(job)
        p_in, p_out = prices.get(model, (0.0, 0.0))
        est = n_in * p_in + n_out * p_out

        print(f"\n{job.name}  model={model}")
        print(f"  trials        : {trials} completed, {errored} errored")
        print(f"  input tokens  : {n_in:,}  (codex reports {n_cache:,} cached, "
              f"{n_cache/n_in:.0%})" if n_in else "  input tokens  : 0")
        print(f"  output tokens : {n_out:,}")
        if not model or model not in prices:
            print(f"  no list price for {model!r}; cannot estimate")
            continue
        print(f"  list-price est: ${est:,.4f} (upper bound, ignores cache discount)")
        if trials:
            per = est / trials
            print(f"  per task      : ${per:,.4f}")
            print(f"  projected x{args.extrapolate_to} : ${per * args.extrapolate_to:,.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
