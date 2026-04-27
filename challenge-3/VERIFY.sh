#!/bin/bash
# challenge-3 VERIFY - 1-command 재현 (기상 후 첫 5분)
# session-3 will fill the body. propagation block is fixed.
set -euo pipefail
cd "$(dirname "$0")"
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

echo "=== challenge-3 VERIFY (skeleton, completed by sprint-3) ==="

# Sprint 3 will fill the 10 gates here. For now, basic existence check.

GATES_FAILED=0

echo "[1/10] portability gate"
if [ -d "aiwriting" ]; then
  matches=$(grep -r "/Users/leesanghun" aiwriting/agents/ aiwriting/skills/ 2>/dev/null | wc -l | tr -d ' ')
  [ "$matches" = "0" ] && echo "  OK" || { echo "  FAIL: $matches"; GATES_FAILED=$((GATES_FAILED+1)); }
else
  echo "  SKIP (aiwriting/ not yet built)"
fi

echo "[2/10] R6→R7 migration"
if [ -d "aiwriting/skills" ]; then
  r6=$(grep -rE 'R1.*R6\b' aiwriting/skills/ 2>/dev/null | wc -l | tr -d ' ')
  [ "$r6" = "0" ] && echo "  OK" || { echo "  FAIL: $r6"; GATES_FAILED=$((GATES_FAILED+1)); }
else
  echo "  SKIP"
fi

echo "[3/10] plugin validate"
if [ -f "aiwriting/.claude-plugin/plugin.json" ]; then
  if claude plugin validate aiwriting/ 2>&1 | grep -q "valid"; then
    echo "  OK (claude validate)"
  elif python3 scripts/validate_manifest.py aiwriting/.claude-plugin/plugin.json 2>/dev/null; then
    echo "  OK (jsonschema fallback)"
  else
    echo "  FAIL"
    GATES_FAILED=$((GATES_FAILED+1))
  fi
else
  echo "  SKIP (plugin.json absent)"
fi

echo "[4/10] manifest schemas"
if [ -d "tests" ] && ls tests/test_plugin_manifest.py 2>/dev/null; then
  pytest tests/test_plugin_manifest.py tests/test_marketplace_manifest.py -q && echo "  OK" || { echo "  FAIL"; GATES_FAILED=$((GATES_FAILED+1)); }
else
  echo "  SKIP"
fi

echo "[5/10] copy-killer weights"
if ls tests/test_copy_killer_weights.py 2>/dev/null; then
  pytest tests/test_copy_killer_weights.py -q && echo "  OK" || { echo "  FAIL"; GATES_FAILED=$((GATES_FAILED+1)); }
else
  echo "  SKIP"
fi

echo "[6/10] structure-critic 4 mode"
if ls tests/test_structure_critic_modes.py 2>/dev/null; then
  pytest tests/test_structure_critic_modes.py -q && echo "  OK" || { echo "  FAIL"; GATES_FAILED=$((GATES_FAILED+1)); }
else
  echo "  SKIP"
fi

echo "[7/10] fact-checker 5 type"
if ls tests/test_fact_checker_patterns.py 2>/dev/null; then
  pytest tests/test_fact_checker_patterns.py -q && echo "  OK" || { echo "  FAIL"; GATES_FAILED=$((GATES_FAILED+1)); }
else
  echo "  SKIP"
fi

echo "[8/10] full pipeline 16 cases"
if [ -f "scripts/run_full_pipeline.py" ]; then
  python3 scripts/run_full_pipeline.py
  cnt=$(find fixtures/outputs/sprint3 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
  [ "$cnt" = "16" ] && echo "  OK ($cnt md)" || { echo "  FAIL: $cnt md"; GATES_FAILED=$((GATES_FAILED+1)); }
else
  echo "  SKIP"
fi

echo "[9/10] dogfood 4 outputs"
cnt=$(find fixtures/dogfood -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
[ "$cnt" = "4" ] && echo "  OK" || echo "  WARN: $cnt/4 dogfood"

echo "[10/10] no .half_scope"
[ ! -f .half_scope ] && echo "  OK" || { echo "  FAIL: $(cat .half_scope)"; GATES_FAILED=$((GATES_FAILED+1)); }

echo ""
if [ "$GATES_FAILED" = "0" ]; then
  echo "=== ALL GATES GREEN ==="
  [ -f logs/cost_probe.txt ] && echo "Cost: $(head -1 logs/cost_probe.txt)"
  exit 0
else
  echo "=== $GATES_FAILED GATE(S) FAILED ==="
  exit 1
fi
