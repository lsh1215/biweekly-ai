#!/bin/bash
# challenge-3 sprint 3 checkpoint - filled in by session-3
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

# cascade skip
[ -f .half_scope ] && { echo "HALF_SCOPE: $(cat .half_scope) - sprint3 skip"; exit 0; }

# stub guard - session-3 will replace
if [ ! -f "aiwriting/agents/aiwriting-fact-checker.md" ]; then
  echo "sprint3 STUB - session-3 must implement"
  exit 1
fi

echo "sprint3 stub-pass"
