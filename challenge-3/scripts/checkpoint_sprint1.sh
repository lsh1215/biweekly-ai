#!/bin/bash
# challenge-3 sprint 1 checkpoint - filled in by session-1
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

# cascade skip
[ -f .half_scope ] && { echo "HALF_SCOPE: $(cat .half_scope) - sprint1 skip"; exit 0; }

# stub guard - session-1 will replace
if [ ! -f "aiwriting/skills/cover-letter/SKILL.md" ]; then
  echo "sprint1 STUB - session-1 must implement"
  exit 1
fi

echo "sprint1 stub-pass"
