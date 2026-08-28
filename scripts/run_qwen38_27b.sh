#!/bin/bash
# Run GameCraft-Bench with the locally-hosted Qwen3.8-27B as the coding agent.
#
# The agent talks to the vLLM server started by ../serve_qwen38_27b.sh
# (OpenAI-compatible, 127.0.0.1:8038). The verifier judge is deliberately NOT
# touched: it keeps using GAMECRAFT_BENCH_JUDGE_* from .env (gpt-5.5 via
# OpenRouter) so scores stay comparable with every other model on the board.
#
# Usage:
#   ./scripts/run_qwen38_27b.sh -p tasks/puzzle-sokoban-dungeon
#   ./scripts/run_qwen38_27b.sh -p tasks -n 4 --job-name qwen38-full
#
# Env overrides:
#   QWEN_URL=http://127.0.0.1:8038/v1   vLLM endpoint
#   QWEN_MODEL=qwen38-27b               served-model-name
#   QWEN_EFFORT=xhigh                   reasoning effort (xhigh|medium|low)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi

if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    source ".env"
    set +a
fi

export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"

QWEN_URL="${QWEN_URL:-http://127.0.0.1:8038/v1}"
QWEN_MODEL="${QWEN_MODEL:-qwen38-27b}"
# Codex defaults to reasoning_effort=high, which Qwen3.8 rejects outright
# ("Supported types are xhigh (default), medium, and low"). xhigh is the
# model's own default, i.e. the faithful "full strength" setting.
QWEN_EFFORT="${QWEN_EFFORT:-xhigh}"

# Fail fast rather than burning a sandbox build on a dead endpoint.
if ! curl -sf "${QWEN_URL%/v1}/health" >/dev/null 2>&1; then
    echo "error: no vLLM server at $QWEN_URL — start it with ../serve_qwen38_27b.sh start" >&2
    exit 1
fi

# Agent creds. vLLM ignores the key but the OpenAI SDK insists on one.
# Harbor's provider resolution reads these from the host env; --ae forwards
# them into the sandbox where the codex CLI actually runs.
export OPENAI_BASE_URL="$QWEN_URL"
export OPENAI_API_KEY="${OPENAI_API_KEY:-vllm-local}"

# Default to --no-delete unless the caller passed an explicit choice.
delete_flag="--no-delete"
for arg in "$@"; do
    case "$arg" in
        --delete|--no-delete) delete_flag=""; break ;;
    esac
done

: "${GAMECRAFT_BENCH_JOBS_ROOT:=$REPO_ROOT/../gamecraft-bench-jobs}"
mkdir -p "$GAMECRAFT_BENCH_JOBS_ROOT"

# The local server is a single 2-GPU replica; let the caller raise it but keep
# the default low so concurrent trials do not queue behind each other.
concurrency_set=0
for arg in "$@"; do
    case "$arg" in
        -n|--n-concurrent) concurrency_set=1 ;;
    esac
done
concurrency_flags=()
if [ "$concurrency_set" -ne 1 ]; then
    concurrency_flags=(-n 2)
fi

# Let an explicit --ak reasoning_effort=... from the caller win.
effort_set=0
for arg in "$@"; do
    case "$arg" in
        reasoning_effort=?*) effort_set=1 ;;
    esac
done
effort_flags=()
if [ "$effort_set" -ne 1 ]; then
    effort_flags=(--ak "reasoning_effort=$QWEN_EFFORT")
fi

echo ">> agent : $QWEN_MODEL @ $QWEN_URL (reasoning_effort=$QWEN_EFFORT)"
echo ">> judge : ${GAMECRAFT_BENCH_JUDGE:-openai} / ${GAMECRAFT_BENCH_JUDGE_MODEL:-<backend default>} (unchanged)"
echo ">> jobs  : $GAMECRAFT_BENCH_JOBS_ROOT"

exec harbor run \
    --environment-import-path gamecraft_bench.local_env:LocalSubprocessEnvironment \
    --agent-import-path gamecraft_bench.local_agents:LocalCodex \
    --jobs-dir "$GAMECRAFT_BENCH_JOBS_ROOT" \
    --model "$QWEN_MODEL" \
    --ae "OPENAI_API_KEY=$OPENAI_API_KEY" \
    --ae "OPENAI_BASE_URL=$OPENAI_BASE_URL" \
    "${effort_flags[@]}" \
    "${concurrency_flags[@]}" \
    ${delete_flag} \
    "$@"
