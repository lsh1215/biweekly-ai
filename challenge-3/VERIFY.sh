#!/bin/bash
# challenge-3 VERIFY - 1-command 재현 (기상 후 첫 5분).
# 10 hard gates per VERIFY.md. set -u not -e: we accumulate failures and exit at end.
set -uo pipefail
cd "$(dirname "$0")"
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

echo "=== challenge-3 VERIFY (10 gates) ==="
GATES_FAILED=0

# 1 — portability
echo "[1/10] portability gate (no /Users/leesanghun in plugin)"
matches=$( { grep -r "/Users/leesanghun" aiwriting/agents/ aiwriting/skills/ 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$matches" = "0" ]; then echo "  OK"; else echo "  FAIL ($matches)"; GATES_FAILED=$((GATES_FAILED+1)); fi

# 2 — R6 → R7 migration
echo "[2/10] R6→R7 migration"
r6=$( { grep -rE 'R1.*R6\b' aiwriting/skills/ 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$r6" = "0" ]; then echo "  OK"; else echo "  FAIL ($r6 stale R1-R6 refs)"; GATES_FAILED=$((GATES_FAILED+1)); fi

# 3 — plugin validate
echo "[3/10] plugin validate (claude or jsonschema fallback)"
if claude plugin validate aiwriting/ 2>&1 | grep -q "valid"; then
  echo "  OK (claude validate)"
elif python3 scripts/validate_manifest.py aiwriting/.claude-plugin/plugin.json >/dev/null 2>&1 \
  && python3 scripts/validate_manifest.py aiwriting/.claude-plugin/marketplace.json >/dev/null 2>&1; then
  echo "  OK (jsonschema fallback)"
else
  echo "  FAIL"; GATES_FAILED=$((GATES_FAILED+1))
fi

# 4 — manifest schemas (pytest)
echo "[4/10] manifest schemas pytest"
if pytest tests/test_plugin_manifest.py tests/test_marketplace_manifest.py -q >/dev/null 2>&1; then
  echo "  OK"
else
  echo "  FAIL"; GATES_FAILED=$((GATES_FAILED+1))
fi

# 5 — copy-killer weights
echo "[5/10] copy-killer weights = 1.0, threshold = 0.35"
if pytest tests/test_copy_killer_weights.py -q >/dev/null 2>&1; then
  echo "  OK"
else
  echo "  FAIL"; GATES_FAILED=$((GATES_FAILED+1))
fi

# 6 — structure-critic 4 mode
echo "[6/10] structure-critic 4 mode section"
if pytest tests/test_structure_critic_modes.py -q >/dev/null 2>&1; then
  echo "  OK"
else
  echo "  FAIL"; GATES_FAILED=$((GATES_FAILED+1))
fi

# 7 — fact-checker 5 type
echo "[7/10] fact-checker 5 hard-evidence types"
if pytest tests/test_fact_checker_patterns.py -q >/dev/null 2>&1; then
  echo "  OK"
else
  echo "  FAIL"; GATES_FAILED=$((GATES_FAILED+1))
fi

# 8 — full pipeline 16 cases
echo "[8/10] full pipeline 16 cases (writer-replay → scrub → ck → fc)"
if python3 scripts/run_full_pipeline.py >/dev/null 2>&1; then
  md_count=$(find fixtures/outputs/sprint3 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
  json_count=$(find fixtures/outputs/sprint3 -name '*.report.json' 2>/dev/null | wc -l | tr -d ' ')
  if [ "$md_count" = "16" ] && [ "$json_count" = "16" ]; then
    echo "  OK ($md_count md, $json_count report.json)"
  else
    echo "  FAIL (md=$md_count json=$json_count)"; GATES_FAILED=$((GATES_FAILED+1))
  fi
else
  echo "  FAIL (run_full_pipeline returned non-zero)"; GATES_FAILED=$((GATES_FAILED+1))
fi

# 9 — dogfood 4 outputs (warn, not fail; sprint-3 final live step)
echo "[9/10] dogfood 4 outputs"
dog_count=$(find fixtures/dogfood -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
if [ "$dog_count" = "4" ]; then
  echo "  OK ($dog_count/4 dogfood md)"
else
  echo "  WARN ($dog_count/4 dogfood — re-run scripts/dogfood.sh to populate)"
fi

# 10 — no .half_scope
echo "[10/10] no .half_scope flag"
if [ ! -f .half_scope ]; then
  echo "  OK"
else
  echo "  FAIL (.half_scope=$(cat .half_scope))"; GATES_FAILED=$((GATES_FAILED+1))
fi

echo ""
if [ "$GATES_FAILED" = "0" ]; then
  echo "=== ALL GATES GREEN ==="
  [ -f logs/cost_probe.txt ] && head -1 logs/cost_probe.txt
  exit 0
else
  echo "=== $GATES_FAILED GATE(S) FAILED ==="
  exit 1
fi
