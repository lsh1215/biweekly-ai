#!/bin/bash
# challenge-3 sprint 3 checkpoint - fact-checker + orchestrator + dogfood + VERIFY.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

# cascade skip
[ -f .half_scope ] && { echo "HALF_SCOPE: $(cat .half_scope) - sprint3 skip"; exit 0; }

# idempotent reset
rm -rf fixtures/outputs/sprint3/
mkdir -p fixtures/outputs/sprint3/

# 1. fact-checker artifacts present
[ -f "aiwriting/agents/aiwriting-fact-checker.md" ] || { echo "ERR: fact-checker agent missing"; touch .half_scope; exit 1; }
[ -f "scripts/fact_checker.py" ]                    || { echo "ERR: fact_checker.py missing"; touch .half_scope; exit 1; }
[ -f "scripts/fact_checker_patterns.py" ]           || { echo "ERR: fact_checker_patterns.py missing"; touch .half_scope; exit 1; }
[ -f "known_facts.yml.example" ]                    || { echo "ERR: known_facts.yml.example missing"; touch .half_scope; exit 1; }

# 2. orchestrator picker present + user-invocable
grep -q "1.*blog" aiwriting/skills/aiwriting/SKILL.md      || { echo "ERR: picker '1. blog' missing"; touch .half_scope; exit 1; }
grep -q "user-invocable: true" aiwriting/skills/aiwriting/SKILL.md || { echo "ERR: orchestrator not user-invocable"; touch .half_scope; exit 1; }

# 3. portability + R6→R7  (grep returns 1 on no-match; tolerate)
matches=$( { grep -r "/Users/leesanghun" aiwriting/agents/ aiwriting/skills/ 2>/dev/null || true; } | wc -l | tr -d ' ')
[ "$matches" = "0" ] || { echo "ERR: $matches portability matches"; touch .half_scope; exit 1; }
r6=$( { grep -rE 'R1.*R6\b' aiwriting/skills/ 2>/dev/null || true; } | wc -l | tr -d ' ')
[ "$r6" = "0" ] || { echo "ERR: $r6 R6 stale"; touch .half_scope; exit 1; }
echo "  portability OK; R6 stale=$r6"

# 4. all tests
pytest tests/ -q || { echo "ERR: pytest failed"; touch .half_scope; exit 4; }

# 5. full pipeline 16 cases
python3 scripts/run_full_pipeline.py
md_count=$(find fixtures/outputs/sprint3 -name '*.md' | wc -l | tr -d ' ')
json_count=$(find fixtures/outputs/sprint3 -name '*.report.json' | wc -l | tr -d ' ')
[ "$md_count" = "16" ]  || { echo "ERR: $md_count md (want 16)"; exit 6; }
[ "$json_count" = "16" ] || { echo "ERR: $json_count report.json (want 16)"; exit 6; }

# 6. structure-critic REJECT count
rejects=$(python3 -c "
import json, glob
print(sum(1 for f in glob.glob('fixtures/outputs/sprint3/*.report.json') if json.load(open(f)).get('structure_critic',{}).get('verdict') == 'REJECT'))
")
[ "$rejects" = "0" ] || { echo "ERR: REJECT count $rejects (want 0)"; touch .half_scope; exit 7; }

# 7. plugin validate (S1 fallback safe)
if claude plugin validate aiwriting/ 2>&1 | grep -q "valid"; then
  echo "  plugin validate: claude OK"
elif python3 scripts/validate_manifest.py aiwriting/.claude-plugin/plugin.json 2>/dev/null \
  && python3 scripts/validate_manifest.py aiwriting/.claude-plugin/marketplace.json 2>/dev/null; then
  echo "  plugin validate: jsonschema fallback OK"
else
  echo "ERR: plugin validate failed (no claude + jsonschema fallback failed)"
  touch .half_scope
  exit 2
fi

echo "sprint3 OK (pre-dogfood)"
echo "  md=${md_count} reports=${json_count} rejects=${rejects}"
