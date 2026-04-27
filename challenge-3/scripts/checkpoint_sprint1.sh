#!/bin/bash
# challenge-3 sprint 1 checkpoint - skeleton, body filled in by sprint-1
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

# cascade skip (CLAUDE.md half_scope rule)
[ -f .half_scope ] && { echo "HALF_SCOPE: $(cat .half_scope) - sprint1 skip"; exit 0; }

# stub guard - sprint-1 will replace this body. exit 1 so overnight.sh runs session-1.
if [ ! -f "aiwriting/skills/cover-letter/SKILL.md" ]; then
  echo "sprint1 STUB - to be filled in sprint1"
  exit 1
fi

echo "sprint1 stub-pass"
