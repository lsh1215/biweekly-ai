#!/bin/bash
# challenge-3 sprint 0 checkpoint
# Critic C2: shared 4-line propagation block at top of all 5 .sh files.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

# 멱등화 (CLAUDE.md §10) - safe re-entry
rm -f logs/cost_probe.txt logs/cost_probe.json
rm -rf .pytest_cache

# 1. portability gate (Critic C3) — grep returns 1 on no-match; tolerate via `|| true`
matches=$( { grep -r "/Users/leesanghun" aiwriting/agents/ aiwriting/skills/ 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$matches" != "0" ]; then
  echo "ERR: $matches absolute path matches in plugin"
  touch .half_scope
  exit 1
fi
echo "[1/8] portability OK ($matches matches)"

# 2. R6 -> R7 migration (Critic C3) - no stale R1-R6 in skills/agents
r6_skills=$( { grep -rE 'R1.{0,3}R6\b' aiwriting/skills/ 2>/dev/null || true; } | wc -l | tr -d ' ')
r6_agents=$( { grep -rE 'R1.{0,3}R6\b' aiwriting/agents/ 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$r6_skills" != "0" ] || [ "$r6_agents" != "0" ]; then
  echo "ERR: $r6_skills R6-stale matches in skills, $r6_agents in agents"
  touch .half_scope
  exit 1
fi
echo "[2/8] R6->R7 migration OK"

# 3. plugin validate (S1 fallback)
if command -v claude >/dev/null 2>&1 && claude plugin validate aiwriting/ 2>&1 | grep -q "valid"; then
  echo "[3/8] validate OK (claude plugin validate)"
elif python3 scripts/validate_manifest.py aiwriting/.claude-plugin/plugin.json; then
  echo "[3/8] validate OK (jsonschema fallback)"
else
  echo "ERR: plugin validate failed (both paths)"
  touch .half_scope
  exit 2
fi

# 4. tests (TDD strict)
echo "[4/8] running pytest..."
pytest tests/test_path_portability.py \
       tests/test_r6_to_r7_migration.py \
       tests/test_plugin_manifest.py \
       tests/test_marketplace_manifest.py \
       tests/test_phase5_graceful_skip.py \
       tests/test_propagation.py -q || { touch .half_scope; exit 4; }

# 5. cost_probe (M5 - static estimation only, no live calls)
echo "[5/8] cost_probe..."
python3 scripts/cost_probe.py
head -1 logs/cost_probe.txt | grep -qE '^estimated_total_usd=[0-9.]+' || { echo "ERR: cost_probe.txt malformed"; exit 5; }

# 6. fixture inputs (D10 - 16 yml = 4 format x 4 topic)
n=$(find fixtures/inputs -name '*.yml' 2>/dev/null | wc -l | tr -d ' ')
if [ "$n" != "16" ]; then
  echo "ERR: expected 16 fixture inputs, got $n"
  touch .half_scope
  exit 6
fi
echo "[6/8] fixture inputs OK ($n yml)"

# 7. known_facts.yml.example exists
[ -f known_facts.yml.example ] || { echo "ERR: known_facts.yml.example missing"; touch .half_scope; exit 7; }
echo "[7/8] known_facts.yml.example OK"

# 8. propagation auto-verify (Critic C2)
missing=$( { grep -L 'source .venv/bin/activate' \
  scripts/checkpoint_sprint0.sh \
  scripts/checkpoint_sprint1.sh \
  scripts/checkpoint_sprint2.sh \
  scripts/checkpoint_sprint3.sh \
  VERIFY.sh 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$missing" != "0" ]; then
  echo "ERR: $missing files missing .venv propagation"
  touch .half_scope
  exit 9
fi
echo "[8/8] propagation OK (5 files all source .venv)"

# Note: docker compose v1 hyphen check is enforced by tests/test_propagation.py
# (test_no_docker_compose_dash). It runs in step 4 above.

echo "sprint0 OK"
