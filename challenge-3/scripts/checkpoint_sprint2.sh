#!/bin/bash
# challenge-3 sprint 2 checkpoint - filled in by session-2
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

# cascade skip
[ -f .half_scope ] && { echo "HALF_SCOPE: $(cat .half_scope) - sprint2 skip"; exit 0; }

# stub guard - session-2 will replace
if [ ! -f "aiwriting/agents/aiwriting-copy-killer.md" ]; then
  echo "sprint2 STUB - session-2 must implement"
  exit 1
fi

echo "sprint2 stub-pass"
