#!/bin/bash
# challenge-3 sprint 2 checkpoint
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

# cascade skip
[ -f .half_scope ] && { echo "HALF_SCOPE: $(cat .half_scope) - sprint2 skip"; exit 0; }

echo "[sprint2] step 1/9 — 3 sprint-2 agent files exist"
for a in scrubber copy-killer structure-critic; do
  [ -f "aiwriting/agents/aiwriting-${a}.md" ] || { echo "  ERR: missing aiwriting-${a}.md"; touch .half_scope; exit 1; }
done

echo "[sprint2] step 2/9 — structure-critic 4 mode + Common section"
python3 - <<'PY'
import re, sys
content = open('aiwriting/agents/aiwriting-structure-critic.md').read()
modes = re.findall(r'^## Mode:\s*(blog|cover-letter|paper|letter)\s*$', content, re.MULTILINE)
if set(modes) != {'blog','cover-letter','paper','letter'}:
    print(f'  ERR: modes={modes}'); sys.exit(1)
if not re.search(r'^## Common\s*$', content, re.MULTILINE):
    print('  ERR: ## Common section missing'); sys.exit(1)
PY

echo "[sprint2] step 3/9 — portability + R6→R7 propagation"
set +e
matches=$(grep -r "/Users/leesanghun" aiwriting/agents/ aiwriting/skills/ 2>/dev/null | wc -l | tr -d ' ')
r6=$(grep -rE 'R1.*R6\b' aiwriting/skills/ 2>/dev/null | wc -l | tr -d ' ')
set -e
[ "$matches" = "0" ] || { echo "  ERR: $matches absolute path matches"; touch .half_scope; exit 1; }
[ "$r6" = "0" ] || { echo "  ERR: $r6 R6 stale"; touch .half_scope; exit 1; }

echo "[sprint2] step 4/9 — 16 critic replays present + D7 7-key shape"
python3 - <<'PY'
import json, glob, sys
required = {'model','captured_at','stage','request','response','dispatch_key','format'}
files = sorted(glob.glob('replay/fixtures/*/*-critic.json'))
if len(files) != 16:
    print(f'  ERR: expected 16 critic replays, found {len(files)}'); sys.exit(1)
for f in files:
    d = json.load(open(f))
    missing = required - set(d.keys())
    if missing:
        print(f'  ERR: {f} missing {missing}'); sys.exit(1)
    if d['stage'] != 'structure-critic':
        print(f'  ERR: {f} stage={d["stage"]}'); sys.exit(1)
print(f'  OK 16 critic fixtures shape')
PY

echo "[sprint2] step 5/9 — pytest sprint-2 TDD suite"
pytest tests/test_copy_killer_weights.py \
       tests/test_copy_killer_metric_sentence_length_variance.py \
       tests/test_copy_killer_metric_avg_syllable_length.py \
       tests/test_copy_killer_metric_connector_frequency.py \
       tests/test_copy_killer_metric_r1_r7_residual.py \
       tests/test_copy_killer_metric_monotone_ending_ratio.py \
       tests/test_copy_killer_metric_generic_modifier_density.py \
       tests/test_copy_killer_threshold_tuning.py \
       tests/test_structure_critic_modes.py \
       tests/test_e2e_replay_critic.py \
       tests/test_sprint2_pipeline_smoke.py \
       -q || { touch .half_scope; exit 4; }

echo "[sprint2] step 6/9 — run sprint-2 pipeline (16 × scrubber+copy-killer+critic-replay)"
python3 scripts/run_sprint2_pipeline.py | tee logs/sprint2_pipeline.log
[ "$(find fixtures/outputs/sprint2 -name '*.md' | wc -l | tr -d ' ')" = "16" ] || { echo "  ERR: !=16 .md outputs"; touch .half_scope; exit 6; }
[ "$(find fixtures/outputs/sprint2 -name '*.report.json' | wc -l | tr -d ' ')" = "16" ] || { echo "  ERR: !=16 .report.json outputs"; touch .half_scope; exit 6; }

echo "[sprint2] step 7/9 — copy-killer fail-rate & threshold tuning record"
python3 - <<'PY' >> TIMELINE.md
import json, glob, datetime
ts = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec='seconds')
scores = []
verdicts = []
for f in sorted(glob.glob('fixtures/outputs/sprint2/*.report.json')):
    d = json.load(open(f))
    scores.append(round(d['copy_killer']['ai_score'], 3))
    verdicts.append(d['copy_killer']['verdict'])
fails = sum(1 for v in verdicts if v == 'BLOCKED')
threshold = json.load(open(sorted(glob.glob('fixtures/outputs/sprint2/*.report.json'))[0]))['copy_killer']['threshold']
print(f'{ts} sprint2 copy-killer scores={scores} fails={fails}/16 threshold={threshold}')
PY

echo "[sprint2] step 8/9 — propagation invariants for downstream sprints"
for s in scripts/checkpoint_sprint3.sh VERIFY.sh; do
  grep -q 'source .venv/bin/activate' "$s" || { echo "  ERR: $s missing .venv block"; touch .half_scope; exit 9; }
done

echo "[sprint2] step 9/9 — soft gate: REJECT count visible (no hard fail)"
python3 - <<'PY'
import json, glob
rejects = sum(1 for f in glob.glob('fixtures/outputs/sprint2/*.report.json')
              if json.load(open(f))['structure_critic']['verdict'] == 'REJECT')
print(f'  structure-critic REJECT count: {rejects}/16 (sprint3 hard-gates this to 0)')
PY

echo "sprint2 OK"
