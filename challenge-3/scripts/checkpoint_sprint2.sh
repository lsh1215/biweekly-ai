#!/bin/bash
# challenge-3 sprint 2 checkpoint - skeleton, body filled in by sprint-2
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

# cascade skip
[ -f .half_scope ] && { echo "HALF_SCOPE: $(cat .half_scope) - sprint2 skip"; exit 0; }

# stub guard - sprint-2 will replace this body. exit 1 so overnight.sh runs session-2.
if [ ! -f "aiwriting/agents/aiwriting-copy-killer.md" ]; then
  echo "sprint2 STUB - to be filled in sprint2"
  exit 1
fi

echo "sprint2 stub-pass"
