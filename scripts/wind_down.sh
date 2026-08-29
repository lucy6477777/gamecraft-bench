#!/usr/bin/env bash
# What to do once no more rounds will be started.
#
#   ./wind_down.sh [--repo user/name] [--dry-run]
#
# Two steps, in this order and no other:
#
#   1. replay_only.py — rebuild recordings from projects already on disk. This
#      costs nothing and must come first: a trial whose replay failed for a
#      local reason (conda's ffmpeg has no x11grab; that cost a whole run's
#      frames once) is repairable, and uploading before repairing it ships a
#      snapshot the judging machine cannot score.
#
#   2. hf_upload.py — publish. Frames are left behind deliberately: they are 95%
#      of the bytes and rejudge.py rebuilds the identical set from the mp4,
#      verified byte-for-byte across two ffmpeg versions. The generated project
#      is archived per trial, or the object count goes from 25k to half a
#      million.
#
# Idempotent. Re-running re-replays what is already replayed (harmless, free)
# and re-uploads to the same repo.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
[ -f "../.env" ] && { set -a; source ../.env; set +a; }

HF_REPO="WenyiWU0111/gamecraft-bench-baselines"
DRY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) HF_REPO="$2"; shift 2 ;;
    --dry-run) DRY="--dry-run"; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

JOBS="$REPO_ROOT/../gamecraft-bench-jobs"
LOG="$REPO_ROOT/../logs_vllm/wind_down.log"
say() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

say "=== 收尾开始 ==="
say "状态: $(.venv/bin/python scripts/sweep_state.py | tr '\n' ' ')"

# ffmpeg without x11grab records nothing and says it succeeded, so the replay
# step is pinned to one that has it -- the same shim the runner uses.
if ! ffmpeg -hide_banner -devices 2>/dev/null | grep -q x11grab; then
  for cand in /usr/bin/ffmpeg /usr/local/bin/ffmpeg; do
    if [ -x "$cand" ] && "$cand" -hide_banner -devices 2>/dev/null | grep -q x11grab; then
      SHIM="$REPO_ROOT/../logs_vllm/ffmpeg_shim"; mkdir -p "$SHIM"
      ln -sf "$cand" "$SHIM/ffmpeg"; export PATH="$SHIM:$PATH"
      say "ffmpeg 换成 $cand（PATH 上那个没有 x11grab）"; break
    fi
  done
fi

say "--- 1/2 免费补全产物 ---"
for job in "$JOBS"/qwen3.8-27b-r*/; do
  [ -d "$job" ] || continue
  say "replay_only $(basename "$job")"
  .venv/bin/python scripts/replay_only.py "$job" 2>&1 | tail -3 | tee -a "$LOG"
done

say "补全后状态: $(.venv/bin/python scripts/sweep_state.py | tr '\n' ' ')"

say "--- 2/2 上传 HF ($HF_REPO) ---"
pairs=()
for job in "$JOBS"/qwen3.8-27b-r*/; do
  [ -d "$job" ] || continue
  n=$(ls "$job"/*/result.json 2>/dev/null | wc -l)
  [ "$n" -gt 0 ] && pairs+=("qwen3.8-27b/$(basename "$job")=$job")
done
for job in "$JOBS"/glm-5.3-flash "$JOBS"/glm-5.3-flash.part1 "$JOBS"/kimi-k2.6.aborted-0414; do
  [ -d "$job" ] || continue
  n=$(ls "$job"/*/result.json 2>/dev/null | wc -l)
  [ "$n" -gt 0 ] && pairs+=("$(basename "$job")=$job")
done
say "打包 ${#pairs[@]} 个 job 目录"
.venv/bin/python scripts/hf_upload.py --repo "$HF_REPO" $DRY "${pairs[@]}" 2>&1 | tee -a "$LOG"
rc=$?
say "=== 收尾结束 (rc=$rc) ==="
exit $rc
