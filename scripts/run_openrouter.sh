#!/bin/bash
# Generation-only GameCraft-Bench runs against OpenRouter.
#
#   ./scripts/run_openrouter.sh <model-key> [harbor args...]
#   ./scripts/run_openrouter.sh qwen38-27b -p tasks/puzzle-sokoban-dungeon --job-name pilot
#   ./scripts/run_openrouter.sh glm-5.3 -p tasks -n 8 --job-name glm53-full
#
# WHAT THIS DOES NOT DO: call the judge. GAMECRAFT_BENCH_JUDGE=stub keeps the
# build check and the Xvfb replay -- both local, neither costs anything -- and
# skips only the paid multimodal scoring. The mp4s and sampled frames the judge
# would have read still land in <trial>/verifier/demos/, so gpt-5.5 can score
# them later on another machine from a HuggingFace snapshot. Reward in
# result.json will read 0.0 for every trial; that is the stub, not the model.
#
# Model keys, and why each provider is pinned: see scripts/or_proxy.py.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

[ -f ".venv/bin/activate" ] && source ".venv/bin/activate"
if [ -f "../.env" ]; then set -a; source "../.env"; set +a; fi
if [ -f ".env"    ]; then set -a; source ".env";    set +a; fi

export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"

KEY="${1:?usage: run_openrouter.sh <qwen38-27b|kimi-k2.6|glm-5.3-flash> [harbor args...]}"
shift

# Held at 262144 for every model even where the endpoint offers more (glm-5.3-flash
# serves 1M): the three runs are compared with each other, the context budget is
# part of the harness, and pilot-5 peaked at 191k. COMPACT must stay below CTX or
# codex never compacts and generation is guillotined mid-file.
CTX=262144
COMPACT=200000

# ---- model registry ---------------------------------------------------------
# PROVIDER is pinned to the highest-precision endpoint OpenRouter offers for the
# model, so all 140 tasks are answered by one set of weights at one quantization.
case "$KEY" in
  # NO PROVIDER PINNING. The requirement is "the model is qwen3.8-27b", not
  # "served by a particular company". OpenRouter already refuses endpoints that
  # cannot serve the request -- the one route that would break a run (Io Net:
  # tools=False, ctx 65,500) is filtered out automatically because every agent
  # request carries tool definitions; measured 12/12. Free routing also stops a
  # single provider's rate limit from killing a trial, which cost 5 trials on
  # kimi and 2 on glm when they were pinned.
  #
  # What this gives up: a fixed quantization. For qwen that is nearly nothing
  # (every endpoint is fp8 or undisclosed since bf16 disappeared on 2026-08-28);
  # for kimi, endpoints range fp4 to bf16, so state the routing in any writeup.
  # Set OR_PROVIDERS="Alibaba Novita" to pin again.
  qwen38-27b)     MODEL="qwen/qwen3.8-27b";     PROVIDERS=""; PORT=8501; EFFORT="xhigh" ;;
  kimi-k2.6)      MODEL="moonshotai/kimi-k2.6"; PROVIDERS=""; PORT=8502; EFFORT="high"  ;;
  # z-ai/glm-5.3 itself is text-only at every provider, and this bench hands the
  # agent a screenshot helper and tells it to look at its own game. Its vision
  # sibling is the runnable member of that family; -flash is smaller, so say so
  # when reporting the number.
  glm-5.3-flash)  MODEL="z-ai/glm-5.3-flash";   PROVIDERS=""; PORT=8503; EFFORT="high"  ;;
  *) echo "error: unknown model key '$KEY' (qwen38-27b|kimi-k2.6|glm-5.3-flash)" >&2; exit 1 ;;
esac
PROVIDERS="${OR_PROVIDERS:-$PROVIDERS}"
EFFORT="${OR_EFFORT:-$EFFORT}"
PORT="${OR_PORT:-$PORT}"

: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY not set (expected in ../.env)}"

# Check the route before building a sandbox. A pin that cannot call tools, or
# cannot see an image, or serves a shorter window than we just told codex about,
# fails in ways that read as a bad model rather than a bad config.
if [ -n "$PROVIDERS" ]; then
    for prov in $PROVIDERS; do
        "$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/or_preflight.py" \
            --model "$MODEL" --provider "$prov" --min-ctx "$CTX" || exit 1
    done
else
    "$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/or_preflight.py" \
        --model "$MODEL" --min-ctx "$CTX" || exit 1
fi

RUN_ROOT="${GAMECRAFT_BENCH_JOBS_ROOT:-$REPO_ROOT/../gamecraft-bench-jobs}"
LOG_ROOT="${OR_LOG_ROOT:-$REPO_ROOT/../logs_vllm}"
mkdir -p "$RUN_ROOT" "$LOG_ROOT"
STAMP="$(date +%Y%m%d-%H%M%S)"
USAGE_LOG="$LOG_ROOT/or_usage_${KEY}_${STAMP}.jsonl"

# ---- provider-pinning proxy -------------------------------------------------
# codex cannot put `provider` in the body, so the proxy does. It also keeps the
# generation ids, which is the only way to get real spend back out of
# OpenRouter afterwards -- see scripts/or_cost.py.
# Reuse is right across rounds of one sweep and wrong once or_proxy.py has
# changed underneath it: the running process still holds the code it was
# started with. Retire a proxy older than its own source, by the pid it wrote
# down -- never by pattern, which on this host matches the caller's own shell.
STALE=""
STAMP="/tmp/or_proxy_${PORT}.stamp"
if [ -f "$STAMP" ]; then
    STALE=$("$REPO_ROOT/.venv/bin/python" - "$STAMP" "$REPO_ROOT/scripts/or_proxy.py" <<'PYEOF'
import json, os, sys
try:
    st = json.load(open(sys.argv[1]))
    if st["src_mtime"] < os.stat(sys.argv[2]).st_mtime:
        print(st["pid"])
except Exception:
    pass
PYEOF
)
fi
if [ -n "$STALE" ] && kill -0 "$STALE" 2>/dev/null; then
    echo ">> proxy on :$PORT predates scripts/or_proxy.py; retiring pid $STALE" >&2
    kill "$STALE" 2>/dev/null || true
    for _ in $(seq 1 20); do kill -0 "$STALE" 2>/dev/null || break; sleep 0.5; done
fi

if curl -sf -o /dev/null "http://127.0.0.1:$PORT/v1/models" 2>/dev/null; then
    echo ">> proxy already up on :$PORT (reusing; its pin/log may differ)" >&2
else
    provider_flags=()
    for prov in $PROVIDERS; do provider_flags+=(--provider "$prov"); done
    # More than one allowed endpoint is only useful if it may actually move
    # between them; `only` still keeps the pool inside PROVIDERS.
    fallback_flag=()
    [ "$(printf '%s\n' $PROVIDERS | wc -l)" -gt 1 ] && fallback_flag=(--allow-fallbacks)
    "$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/or_proxy.py" \
        --port "$PORT" "${provider_flags[@]}" "${fallback_flag[@]}" --log "$USAGE_LOG" \
        > "$LOG_ROOT/or_proxy_${KEY}_${STAMP}.log" 2>&1 &
    PROXY_PID=$!
    trap 'kill $PROXY_PID 2>/dev/null || true' EXIT
    for _ in $(seq 1 40); do
        curl -sf -o /dev/null "http://127.0.0.1:$PORT/v1/models" && break
        sleep 0.5
    done
    curl -sf -o /dev/null "http://127.0.0.1:$PORT/v1/models" || {
        echo "error: proxy failed to start; see $LOG_ROOT/or_proxy_${KEY}_${STAMP}.log" >&2
        exit 1
    }
fi

# ---- codex config -----------------------------------------------------------
# Without these two keys codex trusts its fallback metadata (258400), never
# compacts, and rides into the server's real ceiling. That is exactly how
# pilot-4 died with an empty project. Regenerated per run so CTX stays honest.
CODEX_CFG="$LOG_ROOT/codex_or_${KEY}.toml"
cat > "$CODEX_CFG" <<TOML
# Generated by scripts/run_openrouter.sh -- do not hand-edit.
model_context_window = $CTX
model_auto_compact_token_limit = $COMPACT
TOML

# ---- an ffmpeg that can actually record -------------------------------------
# The replay records the game window with `-f x11grab`, and conda's ffmpeg 7.1.1
# is built without it: every demo dies with "Unknown input format: 'x11grab'",
# the trial still reports success, and the run produces zero frames -- which is
# the whole point of a generation-only sweep. Ubuntu's 4.4.2 at /usr/bin has it.
# Shadow ONLY ffmpeg, via a one-entry shim dir; putting /usr/bin ahead of the
# venv would also swap out python3, which the verifier needs.
if ! ffmpeg -hide_banner -devices 2>/dev/null | grep -q x11grab; then
    good=""
    for cand in /usr/bin/ffmpeg /usr/local/bin/ffmpeg; do
        if [ -x "$cand" ] && "$cand" -hide_banner -devices 2>/dev/null | grep -q x11grab; then
            good="$cand"; break
        fi
    done
    if [ -z "$good" ]; then
        echo "error: no ffmpeg with x11grab on this host; every replay would" >&2
        echo "       fail silently and the sweep would upload no frames." >&2
        exit 1
    fi
    SHIM="$LOG_ROOT/ffmpeg_shim"
    mkdir -p "$SHIM"
    ln -sf "$good" "$SHIM/ffmpeg"
    export PATH="$SHIM:$PATH"
    echo ">> ffmpeg   : $good (shimmed; PATH ffmpeg lacked x11grab)"
else
    echo ">> ffmpeg   : $(command -v ffmpeg) (has x11grab)"
fi

# ---- judge off --------------------------------------------------------------
export GAMECRAFT_BENCH_JUDGE=stub
export GAMECRAFT_BENCH_JUDGE_MODEL=0     # StubJudge parses this as the fixed score

# ---- agent creds ------------------------------------------------------------
export OPENAI_BASE_URL="http://127.0.0.1:$PORT/v1"
export OPENAI_API_KEY="$OPENROUTER_API_KEY"

delete_flag="--no-delete"
for arg in "$@"; do case "$arg" in --delete|--no-delete) delete_flag=""; break ;; esac; done

echo ">> model    : $MODEL  (providers: $PROVIDERS, ctx $CTX, effort $EFFORT)"
echo ">> judge    : stub / fixed 0.0 -- NO scoring, replay artifacts still produced"
echo ">> proxy    : http://127.0.0.1:$PORT/v1"
echo ">> usage    : $USAGE_LOG"
echo ">> jobs     : $RUN_ROOT"

harbor run \
    --environment-import-path gamecraft_bench.local_env:LocalSubprocessEnvironment \
    --agent-import-path gamecraft_bench.local_agents:LocalCodex \
    --jobs-dir "$RUN_ROOT" \
    --model "$MODEL" \
    --ae "OPENAI_API_KEY=$OPENAI_API_KEY" \
    --ae "OPENAI_BASE_URL=$OPENAI_BASE_URL" \
    --ae "GAMECRAFT_BENCH_JUDGE=stub" \
    --ae "GAMECRAFT_BENCH_JUDGE_MODEL=0" \
    --ak "config=$CODEX_CFG" \
    --ak "reasoning_effort=$EFFORT" \
    ${delete_flag} \
    "$@"
