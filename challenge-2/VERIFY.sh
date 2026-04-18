#!/usr/bin/env bash
# challenge-2 end-to-end verification. Run from anywhere.
# All paths are relative to challenge-2/ (set as script dir).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate project venv if present (homebrew PEP 668 blocks global pip).
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/.venv/bin/activate"
fi

log() { printf '[verify] %s\n' "$*" >&2; }
fail() { printf '[verify] FAIL: %s\n' "$*" >&2; exit 1; }

# Preflight — VERIFY uses replay mode, doesn't need live Anthropic auth.
docker compose version >/dev/null 2>&1 || fail "docker compose v2 not available"

# ---- 1. Cleanup
log "[1/10] Cleaning up old containers and reports..."
docker compose down -v >/dev/null 2>&1 || true
rm -rf reports/
mkdir -p reports

# ---- 2. Postgres + pgvector
log "[2/10] Starting Postgres + pgvector..."
docker compose up -d postgres
for i in {1..30}; do
  if docker compose exec -T postgres pg_isready -U ria -d ria >/dev/null 2>&1; then
    break
  fi
  [ "$i" -eq 30 ] && fail "Postgres not ready after 30s"
  sleep 1
done

# ---- 3. Install (stderr preserved for debugging)
log "[3/10] Installing package (editable)..."
pip install -e . 2>reports/pip.log >/dev/null || { cat reports/pip.log >&2; fail "pip install failed"; }

# ---- 4. Pytest regression (single source of truth — Sprint 4 checkpoint does NOT repeat this)
log "[4/10] Running full pytest suite..."
pytest -q --tb=short || fail "pytest failed"

# ---- 5. Fixtures
log "[5/10] Validating fixtures..."
PRICE_COUNT=$(find data/fixtures/prices -name '*.csv' 2>/dev/null | wc -l | tr -d ' ')
NEWS_COUNT=$(find data/fixtures/news -name '*.json' 2>/dev/null | wc -l | tr -d ' ')
FILING_COUNT=$(find data/fixtures/filings -name '*.txt' 2>/dev/null | wc -l | tr -d ' ')
[ "$PRICE_COUNT"  -ge 10 ] || fail "prices fixtures ($PRICE_COUNT < 10)"
[ "$NEWS_COUNT"   -ge 5  ] || fail "news fixtures ($NEWS_COUNT < 5)"
[ "$FILING_COUNT" -ge 5  ] || fail "filing fixtures ($FILING_COUNT < 5)"
log "    prices=$PRICE_COUNT, news=$NEWS_COUNT, filings=$FILING_COUNT"

# ---- 6. Weekly healthcheck (replay mode for determinism + cost control)
log "[6/10] Running weekly healthcheck (replay mode)..."
REPLAY_PATH="tests/fixtures/replay/healthcheck.json"
[ -f "$REPLAY_PATH" ] || fail "replay fixture missing: $REPLAY_PATH (Sprint 2 must record it)"
python -m ria.cli healthcheck \
  --portfolio portfolio.example.yaml \
  --replay "$REPLAY_PATH" \
  --out reports/ \
  >reports/healthcheck.log 2>&1 || { cat reports/healthcheck.log >&2; fail "healthcheck failed"; }
PLANNED=$(find reports -name 'planned_*.md' | head -1)
[ -n "$PLANNED" ] || fail "planned report not generated"
log "    created: $PLANNED"

# ---- 7. Event interrupt (v1 scope: P0 only)
log "[7/10] Processing synthetic events (v1: P0 interrupts only)..."
python -m ria.cli process-events \
  --queue tests/fixtures/synthetic_events/ \
  --portfolio portfolio.example.yaml \
  --out reports/ \
  >reports/events.log 2>&1 || { cat reports/events.log >&2; fail "process-events failed"; }
INTERRUPT=$(find reports -name 'interrupt_P0_*.md' | head -1)
[ -n "$INTERRUPT" ] || fail "P0 interrupt report not generated"
if find reports -name 'interrupt_P1_*.md' 2>/dev/null | grep -q .; then
  fail "P1 event incorrectly generated interrupt (v1 scope: P0 only)"
fi
if find reports -name 'interrupt_P2_*.md' 2>/dev/null | grep -q .; then
  fail "P2 event incorrectly generated interrupt"
fi
log "    created: $INTERRUPT"

# ---- 8. Report content (action verb + citations)
log "[8/10] Validating report content..."
ACTION_RE='BUY|HOLD|REDUCE|WATCH|REVIEW'
head -c 200 "$PLANNED"   | grep -qEi "$ACTION_RE" || fail "planned missing action verb in first 200 chars"
head -c 200 "$INTERRUPT" | grep -qEi "$ACTION_RE" || fail "interrupt missing action verb in first 200 chars"

PLANNED_CITES=$(grep -cE 'https?://|accession' "$PLANNED" || true)
INTERRUPT_CITES=$(grep -cE 'https?://|accession' "$INTERRUPT" || true)
[ "$PLANNED_CITES"   -ge 2 ] || fail "planned citations < 2 (got $PLANNED_CITES)"
[ "$INTERRUPT_CITES" -ge 1 ] || fail "interrupt citations < 1 (got $INTERRUPT_CITES)"
TOTAL_CITES=$((PLANNED_CITES + INTERRUPT_CITES))
[ "$TOTAL_CITES" -ge 3 ] || fail "total citations < 3 (got $TOTAL_CITES)"
log "    action_verb=OK, planned_cites=$PLANNED_CITES, interrupt_cites=$INTERRUPT_CITES, total=$TOTAL_CITES"

# ---- 9. pgvector corpus
log "[9/10] Checking pgvector corpus..."
CHUNK_COUNT=$(docker compose exec -T postgres psql -U ria -d ria -t -c "SELECT COUNT(*) FROM filings_chunks;" | tr -d ' \n')
[ "$CHUNK_COUNT" -ge 10 ] || fail "filings_chunks=$CHUNK_COUNT < 10"
log "    chunks=$CHUNK_COUNT"

# ---- 10. Cost summary (strict parser: first-line 'total $X.XX' literal)
log "[10/10] Checking cost summary..."
[ -f reports/cost_summary.md ] || fail "cost_summary.md not generated"
TOTAL_USD=$(awk 'NR==1 && /^total \$[0-9]+\.[0-9]+/ { gsub(/\$/,"",$2); print $2; exit }' reports/cost_summary.md)
[ -n "$TOTAL_USD" ] || fail "cost_summary.md: first line must be literal 'total \$X.XX' (e.g. 'total \$12.40')"
if awk -v t="$TOTAL_USD" 'BEGIN {exit !(t+0 <= 50)}'; then
  log "    total=\$${TOTAL_USD} / \$50 budget OK"
else
  fail "Claude API cost \$${TOTAL_USD} exceeded \$50 budget"
fi

printf '\n[verify] CHALLENGE-2 VERIFIED \xe2\x9c\x93\n'
