#!/usr/bin/env python3
"""Print the context-growth curve of a codex trial.

Reads the codex rollout jsonl in a harbor job dir and shows, per model call,
how big the conversation got -- which is what tells you whether the served
--max-model-len is enough, how often auto-compaction fires, and whether a turn
died from silent truncation (input + output == max-model-len exactly).

    ./scripts/ctx_curve.py ../gamecraft-bench-jobs/qwen38-pilot-sokoban-5
"""
import glob, json, sys

job = sys.argv[1].rstrip("/")
maxlen = int(sys.argv[2]) if len(sys.argv) > 2 else 262144

# Finished trials keep the rollout in the job dir; a running one still has it
# in the live sandbox CODEX_HOME, so check both.
paths = glob.glob(f"{job}/*/agent/sessions/**/*.jsonl", recursive=True)
if not paths:
    trials = [d.rstrip("/").rsplit("/", 1)[-1] for d in glob.glob(f"{job}/*/")]
    for t in trials:
        paths += glob.glob(
            f"/tmp/gamecraft-bench-sandboxes/{t}__env"
            f"/_tmp/codex-home/sessions/**/*.jsonl", recursive=True)
if not paths:
    sys.exit(f"no codex rollout under {job} yet")

rows, window, compactions = [], None, 0
for line in open(sorted(paths)[-1]):
    d = json.loads(line)
    if d.get("type") != "event_msg":
        continue
    p = d["payload"]
    if p.get("type") == "token_count":
        info = p["info"]
        window = info.get("model_context_window")
        lt = info.get("last_token_usage") or {}
        rows.append((d["timestamp"][11:19], lt.get("input_tokens", 0),
                     lt.get("output_tokens", 0), lt.get("cached_input_tokens", 0)))
    elif "compact" in str(p.get("type", "")).lower():
        compactions += 1

print(f"job    : {job}")
# codex derates the configured window by 5% as its own safety margin, so
# 0.95*maxlen is the expected reading; anything above maxlen (or far below)
# means codex is aiming past the server and will be truncated mid-generation.
print(f"codex model_context_window = {window}   (server --max-model-len = {maxlen})")
if window is not None and not (0.9 * maxlen <= window <= maxlen):
    print(f"  !! MISMATCH -- expected ~{int(0.95*maxlen)}; codex is not aligned "
          "with the server and will be truncated mid-generation")
print(f"calls  : {len(rows)}    auto-compactions: {compactions}")
print()
print(f"{'time':>9} {'input':>8} {'output':>7} {'cached':>8} {'cache%':>7} {'total':>8}")
prev = None
for t, i, o, c in rows:
    tot = i + o
    flag = ""
    if tot >= maxlen:
        flag = "  <-- HIT THE WALL (truncated)"
    if prev is not None and i < prev - 5000:
        flag += "  <-- history shrank (compaction)"
    prev = i
    pct = (100.0 * c / i) if i else 0.0
    print(f"{t:>9} {i:>8} {o:>7} {c:>8} {pct:>6.1f}% {tot:>8}{flag}")

if rows:
    first, last = rows[0][1], rows[-1][1]
    n = max(1, len(rows) - 1)
    tot_in = sum(r[1] for r in rows)
    tot_cached = sum(r[3] for r in rows)
    print()
    print(f"growth : {first} -> {last}  ({(last-first)/n:+.0f} tokens/call over {n} calls)")
    print(f"prefill: {tot_in:,} input tokens total, {tot_cached:,} served from cache "
          f"({100.0*tot_cached/tot_in if tot_in else 0:.1f}%)")
    print(f"headroom: {maxlen - last:,} tokens left before the wall")
