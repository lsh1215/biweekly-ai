#!/usr/bin/env bash
# Sprint 3 gate: severity classifier + event off-cycle loop.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Activate project venv if present (homebrew PEP 668 blocks global pip — Sprint 0 convention).
if [ -f "$ROOT_DIR/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.venv/bin/activate"
fi

echo "[checkpoint-3] pytest classify + event_loop"
pytest tests/test_classify.py tests/test_event_loop.py -q

echo "[checkpoint-3] synthetic events exist"
[ "$(find tests/fixtures/synthetic_events -name '*.json' | wc -l | tr -d ' ')" -ge 3 ]

echo "[checkpoint-3] process-events: P0 interrupt, P1/P2 suppressed (v1 scope), DUP cooldown"
rm -rf reports/interrupt_*.md
# Idempotency: clear cooldown so re-runs aren't fooled by prior entries.
docker compose exec -T postgres psql -U ria -d ria -c "TRUNCATE event_cooldown;" >/dev/null
python -m ria.cli process-events \
  --queue tests/fixtures/synthetic_events/ \
  --portfolio portfolio.example.yaml \
  --out reports/

find reports -name 'interrupt_P0_*.md' | grep -q . || { echo "missing P0 interrupt"; exit 1; }
if find reports -name 'interrupt_P1_*.md' 2>/dev/null | grep -q .; then
  echo "ERROR: P1 event triggered interrupt (v1 scope: P0 only)"
  exit 1
fi
if find reports -name 'interrupt_P2_*.md' 2>/dev/null | grep -q .; then
  echo "ERROR: P2 event triggered interrupt (should be suppressed)"
  exit 1
fi

echo "[checkpoint-3] verify cooldown suppressed DUP event in journal"
DUP_COUNT=$(docker compose exec -T postgres psql -U ria -d ria -t -c \
  "SELECT COUNT(*) FROM decisions WHERE cycle_type='cooldown_skip';" | tr -d ' \n')
[ "$DUP_COUNT" -ge 1 ] || { echo "no cooldown_skip journal entry (DUP event should have been suppressed)"; exit 1; }

echo "[checkpoint-3] PASS"
