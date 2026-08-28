#!/usr/bin/env python3
"""Refuse to start a sweep whose pinned endpoint cannot do the job.

Three ways an OpenRouter route silently ruins a run, all seen for real on this
bench:

  no tools    the agent narrates the whole game instead of writing it and
              scores 0 with a full-looking transcript (qwen pilot-3).
  short ctx   codex is told the window from our config, the endpoint enforces
              its own, and generation is guillotined mid-file (pilot-4). Io Net
              serves qwen/qwen3.8-27b at 65,500 -- both failures from one route.
  no image    the task tells the agent to screenshot its own game and look at
              it; a text-only endpoint 404s and harbor burns all three retries
              (glm-5.3, which has no vision at any provider).

None of these announce themselves as configuration errors, so they are checked
here instead, before a sandbox is built.

    ./or_preflight.py --model z-ai/glm-5.3-flash --provider Z.AI --min-ctx 262144
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def get(url: str, key: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as fh:
        return json.load(fh)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--provider", default=None,
                    help="Endpoint to check. Omit to check the model under free "
                         "routing: at least one endpoint must be able to serve it.")
    ap.add_argument("--min-ctx", type=int, required=True)
    ap.add_argument("--no-image", action="store_true",
                    help="Skip the image-input check (only for a task set that "
                         "never asks the agent to look at anything).")
    args = ap.parse_args()

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        print("preflight: OPENROUTER_API_KEY not set", file=sys.stderr)
        return 1

    try:
        data = get(f"https://openrouter.ai/api/v1/models/{args.model}/endpoints", key)["data"]
    except urllib.error.HTTPError as e:
        print(f"preflight: model {args.model!r} not on OpenRouter ({e.code})", file=sys.stderr)
        return 1

    model_mods = (data.get("architecture") or {}).get("input_modalities") or []
    endpoints = data.get("endpoints") or []

    if args.provider is None:
        # Free routing. OpenRouter drops endpoints that cannot serve the
        # request's parameters, so the question is not "which one" but "is
        # there any". z-ai/glm-5.3 fails here: text-only at every provider,
        # and the bench hands the agent a screenshot helper.
        good = []
        for e in endpoints:
            params = set(e.get("supported_parameters") or [])
            mods = e.get("input_modalities") or model_mods
            if ("tools" in params
                    and (args.no_image or "image" in mods)
                    and (e.get("context_length") or 0) >= args.min_ctx):
                good.append(e.get("provider_name"))
        if not good:
            print(f"preflight FAILED for {args.model} under free routing: no "
                  f"endpoint has tools + {'' if args.no_image else 'image + '}"
                  f"ctx>={args.min_ctx:,}.", file=sys.stderr)
            print(f"           model input_modalities={model_mods}", file=sys.stderr)
            return 1
        print(f">> preflight ok  {args.model} free routing: "
              f"{len(good)}/{len(endpoints)} endpoints qualify ({', '.join(good[:5])}"
              f"{'...' if len(good) > 5 else ''})")
        return 0

    match = [e for e in endpoints if e.get("provider_name") == args.provider]
    if not match:
        names = sorted({e.get("provider_name") for e in endpoints})
        print(f"preflight: {args.model} is not served by {args.provider!r}.\n"
              f"           available: {', '.join(names)}", file=sys.stderr)
        return 1

    ep = match[0]
    params = set(ep.get("supported_parameters") or [])
    mods = ep.get("input_modalities") or model_mods
    ctx = ep.get("context_length") or 0

    problems = []
    if "tools" not in params:
        problems.append("no tool calling -- the agent cannot edit any files")
    if ctx < args.min_ctx:
        problems.append(f"context {ctx:,} < requested {args.min_ctx:,} -- "
                        f"generation will be truncated with no error")
    if not args.no_image and "image" not in mods:
        problems.append(f"no image input (modalities={mods}) -- the screenshot "
                        f"self-check 404s and the trial fails")

    label = (f"{args.model} @ {args.provider}: quant={ep.get('quantization')} "
             f"ctx={ctx:,} tools={'tools' in params} image={'image' in mods}")
    if problems:
        print(f"preflight FAILED for {label}", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(f">> preflight ok  {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
