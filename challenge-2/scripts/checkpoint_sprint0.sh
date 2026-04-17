#!/usr/bin/env bash
# Sprint 0 gate: scaffolding + fixtures + cost probe.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[checkpoint-0] pytest fixtures + schema"
pytest tests/test_fixtures.py tests/test_portfolio_schema.py -q

echo "[checkpoint-0] Postgres reachable"
docker-compose up -d postgres >/dev/null
for i in {1..30}; do
  docker-compose exec -T postgres pg_isready -U ria -d ria >/dev/null 2>&1 && break
  sleep 1
done

echo "[checkpoint-0] cost probe ran and recorded"
python scripts/cost_probe.py > logs/cost_probe.txt
grep -qE 'estimated_total_usd' logs/cost_probe.txt

echo "[checkpoint-0] fixtures present"
test -f data/fixtures/prices/AAPL.csv
test -f data/fixtures/news/AAPL.json
[ "$(find data/fixtures/filings -name '*.txt' | wc -l | tr -d ' ')" -ge 5 ]

echo "[checkpoint-0] PASS"
