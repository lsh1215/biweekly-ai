#!/usr/bin/env bash
# Sprint 1 gate: tools + RAG ingest.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[checkpoint-1] pytest tools"
pytest tests/test_tools_prices.py tests/test_tools_news.py tests/test_tools_rag.py -q

echo "[checkpoint-1] rag_search returns results"
python -c "
from ria.tools.rag import rag_search
results = rag_search('earnings guidance', 3)
assert len(results) >= 1, f'rag_search empty: {results}'
print(f'rag_search ok, top result preview: {str(results[0])[:80]}')
"

echo "[checkpoint-1] filings_chunks count >= 10"
COUNT=$(docker-compose exec -T postgres psql -U ria -d ria -t -c "SELECT COUNT(*) FROM filings_chunks;" | tr -d ' \n')
[ "$COUNT" -ge 10 ] || { echo "filings_chunks=$COUNT < 10"; exit 1; }
echo "    chunks=$COUNT"

echo "[checkpoint-1] PASS"
