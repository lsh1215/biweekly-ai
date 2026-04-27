#!/bin/bash
# challenge-3 sprint 1 checkpoint
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

# replay_stale / auth_locked / lang_leak cascade skip
[ -f .half_scope ] && { echo "HALF_SCOPE: $(cat .half_scope) - sprint1 skip"; exit 0; }

echo "[sprint1] step 1/8 — verify 4 user-invocable skills"
for fmt in blog cover-letter paper letter; do
  skill="aiwriting/skills/${fmt}/SKILL.md"
  [ -f "$skill" ] || { echo "  ERR: missing $skill"; touch .half_scope; exit 1; }
  grep -q "user-invocable: true" "$skill" || { echo "  ERR: $skill not user-invocable"; touch .half_scope; exit 1; }
done
[ -f "aiwriting/skills/aiwriting/SKILL.md" ] || { echo "  ERR: orchestrator skill missing"; touch .half_scope; exit 1; }
grep -q "user-invocable: true" "aiwriting/skills/aiwriting/SKILL.md" || { echo "  ERR: orchestrator not user-invocable"; touch .half_scope; exit 1; }

echo "[sprint1] step 2/8 — portability + R6→R7 propagation"
# grep returning 1 (no matches) is success here; isolate from set -e/pipefail
set +e
matches=$(grep -r "/Users/leesanghun" aiwriting/agents/ aiwriting/skills/ 2>/dev/null | wc -l | tr -d ' ')
r6=$(grep -rE 'R1.*R6\b' aiwriting/skills/ 2>/dev/null | wc -l | tr -d ' ')
set -e
[ "$matches" = "0" ] || { echo "  ERR: $matches absolute path matches"; touch .half_scope; exit 1; }
[ "$r6" = "0" ] || { echo "  ERR: $r6 R6 stale"; touch .half_scope; exit 1; }

echo "[sprint1] step 3/8 — replay JSON shape (D7 7-key)"
python3 -c "
import json, glob, sys
files = sorted(glob.glob('replay/fixtures/*/*-writer.json'))
if len(files) != 16:
    print(f'ERR: expected 16 writer fixtures, got {len(files)}'); sys.exit(1)
required = {'model','captured_at','stage','request','response','dispatch_key','format'}
for f in files:
    d = json.load(open(f))
    missing = required - set(d.keys())
    if missing:
        print(f'ERR: {f} missing {missing}'); sys.exit(1)
print(f'  OK 16 fixtures shape')
"

echo "[sprint1] step 4/8 — pytest TDD suite"
pytest tests/test_replay_fixture_shape.py tests/test_replay_dispatch_key.py tests/test_writer_format_branching.py tests/test_e2e_replay_writer.py -q || { touch .half_scope; exit 4; }

echo "[sprint1] step 5/8 — render 16 outputs via run_replay.py"
python3 scripts/run_replay.py --all || { touch .half_scope; exit 6; }

echo "[sprint1] step 6/8 — output count"
out_count=$(find fixtures/outputs/sprint1 -name '*.md' | wc -l | tr -d ' ')
[ "$out_count" = "16" ] || { echo "  ERR: $out_count/16 outputs"; touch .half_scope; exit 6; }

echo "[sprint1] step 7/8 — Hangul prose ratio gate (S6, ≥0.20; sprint-1 autonomous decision per TIMELINE)"
python3 -c "
import re, glob, sys
FLOOR = 0.20
fail = 0
for f in sorted(glob.glob('fixtures/outputs/sprint1/*.md')):
    text = open(f).read()
    s = re.sub(r'\`\`\`.*?\`\`\`', '', text, flags=re.DOTALL)
    s = re.sub(r'\`[^\`\n]+\`', '', s)
    h = len(re.findall(r'[가-힣]', s))
    t = len(re.findall(r'\S', s))
    ratio = h / t if t else 0
    if ratio < FLOOR:
        print(f'  LANG_LEAK {f}: prose_ratio={ratio:.2f}')
        fail += 1
    else:
        print(f'  OK {f}: prose_ratio={ratio:.2f}')
sys.exit(1 if fail else 0)
" || { touch .half_scope; exit 8; }

echo "[sprint1] step 8/8 — propagation invariants for downstream sprints"
for s in scripts/checkpoint_sprint2.sh scripts/checkpoint_sprint3.sh VERIFY.sh; do
  grep -q 'source .venv/bin/activate' "$s" || { echo "  ERR: $s missing .venv block"; touch .half_scope; exit 9; }
done

echo "sprint1 OK"
