#!/bin/bash
# Manual replay re-recording. User-triggered only.
#
# Auto recapture is forbidden by D7 (overnight 자동 호출 금지). This script exists so
# the user, after editing prompts or the writer agent body, can deliberately rebuild
# the replay JSON fixtures.
#
# Usage:
#   bash scripts/recapture_replay.sh <fixture-name>   # e.g. blog/kafka-eos
#   bash scripts/recapture_replay.sh all              # rebuild every fixture (live)

set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing"; exit 3; }
source .venv/bin/activate

# Hard-block: this script must never be invoked from overnight.sh.
# overnight.sh runs unattended; recapture should be a deliberate human action.
if [ "${OVERNIGHT_AUTO:-}" = "1" ]; then
  echo "ERR: recapture_replay.sh blocked under OVERNIGHT_AUTO=1 (D7 - auto recapture forbidden)" >&2
  exit 9
fi

target="${1:-}"
if [ -z "$target" ]; then
  echo "Usage: $0 <fixture-name|all>"
  echo "  fixture-name: e.g. blog/kafka-eos (without .yml)"
  echo "  all:          recapture all 16 fixtures via live claude -p calls"
  exit 2
fi

if [ "$target" = "all" ]; then
  echo "[recapture_replay] rebuilding all 16 fixtures via live claude CLI"
  python3 scripts/run_replay_capture.py --source live --all
else
  fixture_path="fixtures/inputs/${target}.yml"
  if [ ! -f "$fixture_path" ]; then
    echo "ERR: fixture not found: $fixture_path"
    exit 4
  fi
  echo "[recapture_replay] rebuilding single fixture: $fixture_path"
  # Single-fixture live recapture: feed via run_replay_capture --all logic but constrained.
  # The synth path is for the autonomous overnight; humans use live.
  python3 - "$fixture_path" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path("scripts").resolve()))
from run_replay_capture import capture_one
out = capture_one(Path(sys.argv[1]), "live")
print(f"WROTE {out}")
PY
fi

echo "[recapture_replay] DONE"
