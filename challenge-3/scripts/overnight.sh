#!/bin/bash
# challenge-3 overnight ralph-thon entry point
# launch: caffeinate -di nohup bash challenge-3/scripts/overnight.sh > challenge-3/logs/overnight.out 2>&1 & disown

set -u
cd "$(dirname "$0")/.."
CHALLENGE_DIR="$(pwd)"
LOG_DIR="$CHALLENGE_DIR/logs"
TIMELINE="$CHALLENGE_DIR/TIMELINE.md"
mkdir -p "$LOG_DIR"

log_timeline() {
  echo "$(date -Iseconds) $*" >> "$TIMELINE"
  echo "$(date -Iseconds) $*"
}

log_timeline "OVERNIGHT_START challenge-3 aiwriting plugin"

run_session() {
  local name="$1" prompt_file="$2" max_turns="${3:-120}"

  # cascade skip
  if [ -f "$CHALLENGE_DIR/.half_scope" ]; then
    log_timeline "$name SKIP - .half_scope=$(cat "$CHALLENGE_DIR/.half_scope")"
    return 0
  fi

  # checkpoint already passed (idempotent restart)
  if bash "$CHALLENGE_DIR/scripts/checkpoint_${name}.sh" 2>/dev/null; then
    log_timeline "$name CHECKPOINT_ALREADY_PASS - skipping execution"
    return 0
  fi

  local attempt=0
  while (( attempt < 5 )); do
    attempt=$((attempt+1))
    local log="$LOG_DIR/${name}.attempt${attempt}.log"
    log_timeline "$name attempt=$attempt"

    claude -p --dangerously-skip-permissions \
      --max-turns "$max_turns" \
      "$(cat "$prompt_file")" \
      > "$log" 2>&1
    local rc=$?

    # rate-limit detection (exit code 독립적, CLAUDE.md 리밋 대응)
    if grep -qiE 'rate.?limit|429|usage limit|quota|reset at|overloaded' "$log"; then
      log_timeline "$name HIT_RATE_LIMIT attempt=$attempt sleeping 5h10m"
      sleep 18600
      continue
    fi

    # checkpoint pass
    if [[ $rc -eq 0 ]] && bash "$CHALLENGE_DIR/scripts/checkpoint_${name}.sh"; then
      log_timeline "$name DONE attempt=$attempt"
      return 0
    fi

    log_timeline "$name FAIL_ATTEMPT attempt=$attempt rc=$rc"
    sleep 300
  done

  log_timeline "$name FAILED_AFTER_5_ATTEMPTS"
  echo "sprint=$name attempts=5" > "$CHALLENGE_DIR/.half_scope"
  return 1
}

# Sprint sequential. cascade skip via .half_scope.
run_session "sprint0" "$CHALLENGE_DIR/prompts/session-0.txt" 100
run_session "sprint1" "$CHALLENGE_DIR/prompts/session-1.txt" 150
run_session "sprint2" "$CHALLENGE_DIR/prompts/session-2.txt" 150
run_session "sprint3" "$CHALLENGE_DIR/prompts/session-3.txt" 150

# 최종 verification
if bash "$CHALLENGE_DIR/VERIFY.sh"; then
  log_timeline "OVERNIGHT_COMPLETE all gates green"
else
  log_timeline "OVERNIGHT_VERIFY_FAIL"
fi
