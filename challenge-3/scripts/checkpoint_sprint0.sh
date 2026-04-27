#!/bin/bash
# challenge-3 sprint 0 checkpoint - filled in by session-0
# (stub. session-0 will overwrite this with EXECUTION_PLAN.md sprint-0 checkpoint body.)
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

# stub guard - session-0 must replace below
if [ ! -f "aiwriting/.claude-plugin/plugin.json" ]; then
  echo "sprint0 STUB - session-0 must implement (no plugin.json yet)"
  exit 1
fi

echo "sprint0 stub-pass (session will replace this body)"
