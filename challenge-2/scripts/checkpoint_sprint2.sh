#!/usr/bin/env bash
# Sprint 2 gate: agent loop + weekly healthcheck.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[checkpoint-2] pytest agent loop + emit_report"
pytest tests/test_agent_loop.py tests/test_emit_report.py -q

echo "[checkpoint-2] weekly healthcheck (replay mode)"
rm -rf reports/planned_*.md
REPLAY_PATH="tests/fixtures/replay/healthcheck.json"
[ -f "$REPLAY_PATH" ] || { echo "replay fixture missing: $REPLAY_PATH"; exit 1; }
python -m ria.cli healthcheck \
  --portfolio portfolio.example.yaml \
  --replay "$REPLAY_PATH" \
  --out reports/

PLANNED=$(find reports -name 'planned_*.md' | head -1)
[ -n "$PLANNED" ] || { echo "no planned report"; exit 1; }

echo "[checkpoint-2] action verb present"
head -c 200 "$PLANNED" | grep -qiE 'BUY|HOLD|REDUCE|WATCH|REVIEW'

echo "[checkpoint-2] citations >= 2"
CITES=$(grep -cE 'https?://|accession' "$PLANNED" || true)
[ "$CITES" -ge 2 ] || { echo "citations=$CITES < 2"; exit 1; }

echo "[checkpoint-2] PASS ($PLANNED, cites=$CITES)"
