#!/usr/bin/env bash
# Overnight outer shell loop for challenge-2. Handles Claude rate limits.
# Per sprint: run session prompt -> detect rate-limit -> sleep 5h10m and retry (max 2x) -> checkpoint gate.
#
# IMPORTANT: 노트북 슬립 방지 필수 (안 하면 sleep 카운터 정지 → 리밋 회복 깨짐).
#   macOS:  caffeinate -di nohup bash scripts/overnight.sh > logs/overnight.out 2>&1 &
#   Linux:  systemd-inhibit --what=sleep nohup bash scripts/overnight.sh &

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

LOG_DIR="$ROOT_DIR/logs"
TIMELINE="$ROOT_DIR/TIMELINE.md"
PROMPTS_DIR="$ROOT_DIR/prompts"
mkdir -p "$LOG_DIR"

iso_now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
timeline() {
  printf -- '- %s %s\n' "$(iso_now)" "$*" >> "$TIMELINE"
}

# ---- Preflight — exit 2 means non-retry (CLAUDE.md 무인 실행 원칙).
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  timeline "PREFLIGHT_FAIL: ANTHROPIC_API_KEY missing"
  exit 2
fi
if ! docker info >/dev/null 2>&1; then
  timeline "PREFLIGHT_FAIL: docker daemon not running"
  exit 2
fi
if ! command -v claude >/dev/null 2>&1; then
  timeline "PREFLIGHT_FAIL: claude CLI not on PATH"
  exit 2
fi

# ---- Sprint selection (safe default).
SPRINTS=("$@")
if [ ${#SPRINTS[@]} -eq 0 ]; then
  SPRINTS=(0 1 2 3 4)
fi

MAX_RETRIES=2
BACKOFF_SECONDS=$((5 * 3600 + 600))   # 5h 10m

run_sprint() {
  local sprint="$1"
  local prompt_file="$PROMPTS_DIR/session-${sprint}.txt"
  local checkpoint="$SCRIPT_DIR/checkpoint_sprint${sprint}.sh"
  local log_file="$LOG_DIR/sprint-${sprint}-$(date +%s).log"

  [ -f "$prompt_file" ] || { timeline "sprint-${sprint} MISSING prompt_file=$prompt_file"; return 2; }
  [ -x "$checkpoint"   ] || { timeline "sprint-${sprint} MISSING checkpoint=$checkpoint";  return 2; }

  # Carry-over cascade: upstream sprint flagged half_scope → skip downstream.
  if [ -f "$ROOT_DIR/.half_scope" ]; then
    timeline "sprint-${sprint} SKIP due_to=$(head -1 "$ROOT_DIR/.half_scope")"
    return 0
  fi

  timeline "sprint-${sprint} START"

  local try=1
  while [ "$try" -le "$MAX_RETRIES" ]; do
    timeline "sprint-${sprint} attempt=${try} log=$log_file"

    claude -p "$(cat "$prompt_file")" --dangerously-skip-permissions >"$log_file" 2>&1
    local rc=$?

    # Rate-limit detection is INDEPENDENT of exit code.
    # Some CLI versions exit 0 while logging the limit message.
    if grep -qiE 'rate.?limit|429|usage limit|quota|reset at|overloaded' "$log_file"; then
      timeline "sprint-${sprint} RATE_LIMIT attempt=${try} sleeping=${BACKOFF_SECONDS}s"
      sleep "$BACKOFF_SECONDS"
      try=$((try + 1))
      continue
    fi

    if [ "$rc" -ne 0 ]; then
      timeline "sprint-${sprint} ERROR exit=${rc} attempt=${try}"
      try=$((try + 1))
      sleep 60   # short generic backoff
      continue
    fi

    if bash "$checkpoint"; then
      timeline "sprint-${sprint} DONE attempt=${try}"
      return 0
    else
      timeline "sprint-${sprint} CHECKPOINT_FAIL attempt=${try}"
      try=$((try + 1))
    fi
  done

  timeline "sprint-${sprint} FAILED after ${MAX_RETRIES} attempts — flagging half_scope"
  echo "HALF_SCOPE_FLAG_SPRINT_${sprint}" >> "$ROOT_DIR/.half_scope"
  return 1
}

timeline "OVERNIGHT_RUN START sprints=${SPRINTS[*]}"

for s in "${SPRINTS[@]}"; do
  if ! run_sprint "$s"; then
    timeline "OVERNIGHT_RUN ABORT at sprint=${s}"
    exit 1
  fi
done

timeline "OVERNIGHT_RUN DONE sprints=${SPRINTS[*]}"
