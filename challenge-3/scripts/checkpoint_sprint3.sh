#!/bin/bash
# challenge-3 sprint 3 checkpoint - skeleton, body filled in by sprint-3
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

# cascade skip
[ -f .half_scope ] && { echo "HALF_SCOPE: $(cat .half_scope) - sprint3 skip"; exit 0; }

# stub guard - sprint-3 will replace this body. exit 1 so overnight.sh runs session-3.
if [ ! -f "aiwriting/agents/aiwriting-fact-checker.md" ]; then
  echo "sprint3 STUB - to be filled in sprint3"
  exit 1
fi

echo "sprint3 stub-pass"
