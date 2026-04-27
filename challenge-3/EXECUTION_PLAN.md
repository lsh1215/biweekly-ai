# challenge-3 EXECUTION_PLAN

**Sprint 분할**: 0/1/2/3 (4개)
**커밋 단위**: Sprint 1개 = 테스트 통과 = 커밋 1개 (CLAUDE.md §6)
**TDD**: 모든 sprint에서 테스트 파일 먼저, 구현 나중 (CLAUDE.md §2)

---

## Sprint 0 — Scaffold + 포팅 + checkpoint propagation 박힌 채 출발

### 입력
- `~/.claude/skills/blog/` 6 file
- `~/.claude/agents/{blog-writer, ai-tell-scrubber, blog-critic}.md`
- PRD §4 디렉토리 레이아웃, §5 path rewrite

### 산출물 (총 30개+)

**Plugin manifest**:
- `aiwriting/.claude-plugin/plugin.json` (metadata 4 필드)
- `aiwriting/.claude-plugin/marketplace.json`
- `aiwriting/README.md` (한계 명시 — copy-killer는 외부 detector 통과 보장 X)
- `aiwriting/LICENSE` (MIT, Copyright (c) 2026 Sanghun Lee)

**포팅 (path rewrite + R6→R7 in-place 교체)**:
- `aiwriting/agents/aiwriting-writer.md` ← `blog-writer.md` 일반화
- `aiwriting/agents/aiwriting-scrubber.md` ← `ai-tell-scrubber.md`
- `aiwriting/skills/blog/{SKILL,philosophy,style-rules,templates,argumentation,ai-tell-rules}.md` ← `~/.claude/skills/blog/`

**Sprint 1~3 stub 파일** (Critic C2 fix — 같은 세션 propagation 박힘):
- `scripts/checkpoint_sprint0.sh` (full)
- `scripts/checkpoint_sprint1.sh` (skeleton with .venv block)
- `scripts/checkpoint_sprint2.sh` (skeleton)
- `scripts/checkpoint_sprint3.sh` (skeleton)
- `VERIFY.sh` (skeleton)

**환경**:
- `challenge-3/.venv/` (D5 forced)
- `challenge-3/requirements.txt` (pytest, pyyaml, regex)
- `scripts/cost_probe.py` (정적 추정, M5)
- `logs/cost_probe.txt`

**Fixture inputs** (D10 lock):
- `fixtures/inputs/blog/{kafka-eos,resilience4j,postgres-upsert,python313-gil}.yml` (4)
- `fixtures/inputs/cover-letter/{fintech-backend-3y,ai-startup-ml-new,enterprise-devops-5y,scale-frontend-2y}.yml` (4)
- `fixtures/inputs/paper/{llm-hallucination,cost-aware-rag,vit-adversarial,fed-learning-noniid}.yml` (4)
- `fixtures/inputs/letter/{thanks-mentor,wedding-friend,condolence-parent,recommendation-grad}.yml` (4)
- `known_facts.yml.example` (사용자 yaml 템플릿)

**Tests** (TDD 우선):
- `tests/test_path_portability.py` — `grep "/Users/leesanghun" → 0`
- `tests/test_r6_to_r7_migration.py` — `grep -rE 'R1.*R6\b' → 0`
- `tests/test_plugin_manifest.py` — 4 필드 정확
- `tests/test_marketplace_manifest.py` — schema
- `tests/test_phase5_graceful_skip.py` — guard 문자열
- `tests/test_propagation.py` — 5 .sh 파일 모두 .venv 블록

### TDD 순서
1. 테스트 5개 파일 작성 (모두 fail)
2. `aiwriting/.claude-plugin/plugin.json` 작성 → `test_plugin_manifest` PASS
3. `aiwriting/.claude-plugin/marketplace.json` 작성 → `test_marketplace_manifest` PASS
4. 포팅 (cp + sed `R1–R6` → `R1–R7`) → `test_path_portability`, `test_r6_to_r7_migration` PASS
5. blog/SKILL.md Phase 5 graceful skip guard 추가 → `test_phase5_graceful_skip` PASS
6. checkpoint_sprint{0,1,2,3}.sh + VERIFY.sh skeleton (5 파일 첫 4 라인 동일 propagation 블록) → `test_propagation` PASS
7. cost_probe.py 작성 → `logs/cost_probe.txt` 생성

### Checkpoint (`scripts/checkpoint_sprint0.sh`)

```bash
#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

# 멱등화
rm -rf logs/cost_probe.txt .pytest_cache

# 1. portability gate (Critic C3)
matches=$(grep -r "/Users/leesanghun" aiwriting/agents/ aiwriting/skills/ 2>/dev/null | wc -l | tr -d ' ')
[ "$matches" = "0" ] || { echo "ERR: $matches absolute path matches"; touch .half_scope; exit 1; }

# 2. R6 → R7 migration (Critic C3)
r6_matches=$(grep -rE 'R1.*R6\b' aiwriting/skills/ 2>/dev/null | wc -l | tr -d ' ')
[ "$r6_matches" = "0" ] || { echo "ERR: $r6_matches R6 stale"; touch .half_scope; exit 1; }

# 3. plugin validate (S1 폴백)
if claude plugin validate aiwriting/ 2>&1 | grep -q "valid"; then
  echo "validate OK"
elif python3 scripts/validate_manifest.py aiwriting/.claude-plugin/plugin.json; then
  echo "fallback validate OK"
else
  touch .half_scope; exit 2
fi

# 4. tests
pytest tests/test_path_portability.py tests/test_r6_to_r7_migration.py tests/test_plugin_manifest.py tests/test_marketplace_manifest.py tests/test_phase5_graceful_skip.py tests/test_propagation.py -q || { touch .half_scope; exit 4; }

# 5. cost_probe
python3 scripts/cost_probe.py
head -1 logs/cost_probe.txt | grep -qE "^estimated_total_usd=[0-9.]+" || exit 5

# 6. fixture inputs 16개
[ "$(find fixtures/inputs -name '*.yml' | wc -l | tr -d ' ')" = "16" ] || exit 6

# 7. propagation 자동 검증 (Critic C2)
missing=$(grep -L 'source .venv/bin/activate' scripts/checkpoint_sprint0.sh scripts/checkpoint_sprint1.sh scripts/checkpoint_sprint2.sh scripts/checkpoint_sprint3.sh VERIFY.sh 2>/dev/null | wc -l | tr -d ' ')
[ "$missing" = "0" ] || { echo "ERR: $missing files missing propagation"; touch .half_scope; exit 9; }

echo "sprint0 OK"
```

### 커밋
`feat(challenge-3): sprint 0 — plugin scaffold + blog port + 5 checkpoint stubs`

---

## Sprint 1 — Format 일반화 (3 skill 추가) + universal writer + replay 라이브 녹화 1회

### 입력
- Sprint 0 산출물
- D1 universal writer + format별 knowledge 세트 (5/2/3/1)
- D7 replay JSON shape

### 산출물

**Skills 추가** (3개, user-invocable):
- `aiwriting/skills/cover-letter/{SKILL.md, philosophy.md, cover-letter-templates.md}` (philosophy는 blog와 공유 — 복사)
- `aiwriting/skills/paper/{SKILL.md, philosophy.md, argumentation.md, paper-templates.md}`
- `aiwriting/skills/letter/{SKILL.md, letter-templates.md}`
- `aiwriting/skills/aiwriting/SKILL.md` (orchestrator, numeric picker D9)

**Universal writer agent**:
- `aiwriting/agents/aiwriting-writer.md` (D1) — Sprint 0 stub을 universal로 확장. format param 분기.

**Replay infrastructure**:
- `replay/fixtures/{format}/{slug}-writer.json` (16개 + structure-critic은 Sprint 2에서)
- `replay/fixtures/{format}/{slug}-critic.json` (16개 — structure-critic verdict)
- `scripts/recapture_replay.sh` (사용자 수동 발동용, 자동 호출 금지)
- `scripts/run_replay.py` (replay loader)

**라이브 녹화 1회** (Sprint 1만): writer + structure-critic 각 16 fixture × 2 stage = 32 호출. 비용 ~$2.10.

**Tests**:
- `tests/test_replay_fixture_shape.py` (D7 7 key)
- `tests/test_replay_dispatch_key.py` (sha256 결정성)
- `tests/test_writer_format_branching.py` — format param에 따라 knowledge file 다른 세트 로드
- `tests/test_e2e_replay_writer.py` — 16 fixture → writer-replay → 출력 .md frontmatter 통과

### TDD 순서
1. `test_replay_fixture_shape.py` (replay JSON 7 key)
2. `test_replay_dispatch_key.py` (sha256)
3. `test_writer_format_branching.py` (format → knowledge 세트)
4. universal writer agent 작성
5. 라이브 녹화 1회 (S5 keychain probe 후 진행. 실패 시 hand-authored 폴백)
6. `test_e2e_replay_writer.py` (16 fixture replay)

### Checkpoint (`scripts/checkpoint_sprint1.sh`)

```bash
#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing"; exit 3; }
source .venv/bin/activate

# replay_stale cascade check
[ -f .half_scope ] && { echo "HALF_SCOPE active: $(cat .half_scope)"; exit 0; }

# 멱등화
rm -rf fixtures/outputs/sprint1/
mkdir -p fixtures/outputs/sprint1/

# 1. 4 skill user-invocable
for fmt in blog cover-letter paper letter; do
  [ -f "aiwriting/skills/${fmt}/SKILL.md" ] || { touch .half_scope; exit 1; }
  grep -q "user-invocable: true" "aiwriting/skills/${fmt}/SKILL.md" || { touch .half_scope; exit 1; }
done
[ -f "aiwriting/skills/aiwriting/SKILL.md" ] || exit 1

# 2. portability + R6 propagation
grep -r "/Users/leesanghun" aiwriting/ && { touch .half_scope; exit 1; } || true
grep -rE 'R1.*R6\b' aiwriting/skills/ && { touch .half_scope; exit 1; } || true

# 3. replay shape
python3 -c "
import json, glob, sys
for f in sorted(glob.glob('replay/fixtures/*/*.json')):
    d = json.load(open(f))
    for k in ['model','captured_at','stage','request','response','dispatch_key','format']:
        assert k in d, f'{f} missing {k}'
print(f'{len(glob.glob(\"replay/fixtures/*/*.json\"))} fixtures shape OK')
"

# 4. tests
pytest tests/test_replay_*.py tests/test_writer_format_branching.py tests/test_e2e_replay_writer.py -q || { touch .half_scope; exit 4; }

# 5. 16 fixture writer 산출물
[ "$(find fixtures/outputs/sprint1 -name '*.md' | wc -l | tr -d ' ')" = "16" ] || exit 6

# 6. Hangul ratio gate (S6)
python3 -c "
import re, glob
for f in glob.glob('fixtures/outputs/sprint1/*.md'):
    text = open(f).read()
    hangul = len(re.findall(r'[가-힣]', text))
    total = len(re.findall(r'\S', text))
    ratio = hangul / total if total else 0
    if ratio < 0.7:
        print(f'LANG_LEAK: {f} ratio={ratio:.2f}')
        exit(1)
"

echo "sprint1 OK"
```

### 커밋
`feat(challenge-3): sprint 1 — universal writer + 4 format skills + replay capture`

---

## Sprint 2 — scrubber 일반화 + copy-killer (LLM-free) + structure-critic (단일 .md, 4 mode)

### 입력
- Sprint 1 산출물 (16 writer 산출 .md)
- D6 copy-killer 가중치 lock
- M2 structure-critic 단일 .md mode section

### 산출물

**Agents**:
- `aiwriting/agents/aiwriting-scrubber.md` 일반화 (Sprint 0 stub을 4 format 적용 가능하게)
- `aiwriting/agents/aiwriting-copy-killer.md` — **LLM 호출 0회**. 정의: "실행 시 `scripts/copy_killer.py <md_path> --threshold 0.35`를 호출하여 ai_score 산출 + PASS/BLOCKED report"
- `aiwriting/agents/aiwriting-structure-critic.md` — 단일 .md + 4 mode section + common section. model: opus.

**Scripts** (LLM-free pure functions):
- `scripts/copy_killer.py` — 6 지표 계산 + score + threshold (D6)
- `scripts/copy_killer_metrics.py` — 6 지표 각 함수 (sentence_length_variance 등)
- `scripts/run_sprint2_pipeline.py` — 16 fixture × scrubber + copy-killer + structure-critic-replay

**Tests** (모두 LLM-free):
- `tests/test_copy_killer_weights.py` — 합 1.0, threshold 0.35
- `tests/test_copy_killer_metric_*.py` (6 지표)
- `tests/test_copy_killer_threshold_tuning.py` — S3 자동 튜닝 룰 결정성
- `tests/test_structure_critic_modes.py` — 4 mode section 단일 .md 파싱
- `tests/test_e2e_replay_critic.py` — 16 critic replay → APPROVE/ITERATE/REJECT verdict 결정성

**Outputs**:
- `fixtures/outputs/sprint2/{format}-{slug}.md` (16, scrubber + copy-killer 통과)
- `fixtures/outputs/sprint2/{format}-{slug}.report.json` (16, copy-killer score + critic verdict)

### TDD 순서
1. `test_copy_killer_weights.py` (합/threshold)
2. `test_copy_killer_metric_*.py` (각 지표)
3. `test_copy_killer_threshold_tuning.py` (S3 룰)
4. `test_structure_critic_modes.py` (4 mode 파싱)
5. `test_e2e_replay_critic.py` (replay 결정성)
6. (그 후 구현)

### Checkpoint (`scripts/checkpoint_sprint2.sh`)

```bash
#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing"; exit 3; }
source .venv/bin/activate

[ -f .half_scope ] && { echo "HALF_SCOPE active"; exit 0; }

# 멱등화
rm -rf fixtures/outputs/sprint2/
mkdir -p fixtures/outputs/sprint2/

# 1. 3 agent 파일
for a in scrubber copy-killer structure-critic; do
  [ -f "aiwriting/agents/aiwriting-${a}.md" ] || { touch .half_scope; exit 1; }
done

# 2. structure-critic 4 mode section
python3 -c "
import re
content = open('aiwriting/agents/aiwriting-structure-critic.md').read()
modes = re.findall(r'## Mode: (blog|cover-letter|paper|letter)', content)
assert set(modes) == {'blog','cover-letter','paper','letter'}, f'modes={modes}'
"

# 3. portability + R6
grep -r "/Users/leesanghun" aiwriting/ && exit 1 || true
grep -rE 'R1.*R6\b' aiwriting/skills/ && exit 1 || true

# 4. tests
pytest tests/test_copy_killer*.py tests/test_structure_critic_modes.py tests/test_e2e_replay_critic.py -q || { touch .half_scope; exit 4; }

# 5. 16 fixture pipeline (scrubber + copy-killer + critic-replay)
python3 scripts/run_sprint2_pipeline.py
[ "$(find fixtures/outputs/sprint2 -name '*.md' | wc -l | tr -d ' ')" = "16" ] || exit 6
[ "$(find fixtures/outputs/sprint2 -name '*.report.json' | wc -l | tr -d ' ')" = "16" ] || exit 6

# 6. copy-killer threshold 분포 TIMELINE 기록
python3 -c "
import json, glob
scores = [json.load(open(f))['copy_killer']['ai_score'] for f in glob.glob('fixtures/outputs/sprint2/*.report.json')]
fails = sum(1 for s in scores if s > 0.35)
print(f'$(date -Iseconds) sprint2 copy-killer scores={scores} fails={fails}/16')
" >> ../TIMELINE.md

echo "sprint2 OK"
```

### 커밋
`feat(challenge-3): sprint 2 — scrubber generalize + copy-killer (LLM-free) + structure-critic`

---

## Sprint 3 — fact-checker (LLM-free) + orchestrator + dogfood 4회 + VERIFY.sh

### 입력
- Sprint 0~2 산출물
- D3 fact-checker 5 type
- D9 orchestrator numeric picker
- D12 dogfood 4회

### 산출물

**Agent**:
- `aiwriting/agents/aiwriting-fact-checker.md` — **LLM 호출 0회**. "실행 시 `scripts/fact_checker.py <md_path> --known known_facts.yml`"

**Scripts**:
- `scripts/fact_checker.py` — 5 type regex (D3) + yaml diff
- `scripts/fact_checker_patterns.py` — 5 type 정의
- `scripts/run_full_pipeline.py` — 16 fixture × 4 deterministic stage (writer-replay/scrubber/copy-killer/fact-checker)
- `scripts/dogfood.sh` — 4 format × 1 topic 라이브 호출 (사용자 깨어난 후 또는 Sprint 3 마지막)

**Plugin orchestrator**:
- `aiwriting/skills/aiwriting/SKILL.md` 완성 (numeric picker, D9)

**Verification**:
- `VERIFY.md` (재현 절차 설명)
- `VERIFY.sh` (Sprint 0에서 stub만 있던 거 완성)
- `RETRO.md` skeleton

**Tests**:
- `tests/test_fact_checker_patterns.py` — 5 type regex 매칭
- `tests/test_full_pipeline_e2e.py` — 16 fixture × 4 stage

**Outputs**:
- `fixtures/outputs/sprint3/{format}-{slug}.md` (16, full pipeline 통과)
- `fixtures/outputs/sprint3/{format}-{slug}.report.json` (16, full report)
- `fixtures/dogfood/{blog,cover-letter,paper,letter}.md` (4, 라이브)

### TDD 순서
1. `test_fact_checker_patterns.py` (5 type)
2. `test_full_pipeline_e2e.py` (16 × 4 stage)
3. `scripts/fact_checker.py` 구현
4. `scripts/run_full_pipeline.py` 구현
5. orchestrator SKILL.md numeric picker 완성
6. VERIFY.sh 완성
7. dogfood 4회 (라이브)
8. RETRO.md skeleton

### Checkpoint (`scripts/checkpoint_sprint3.sh`)

```bash
#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing"; exit 3; }
source .venv/bin/activate

[ -f .half_scope ] && { echo "HALF_SCOPE active"; exit 0; }

# 멱등화
rm -rf fixtures/outputs/sprint3/ fixtures/dogfood/
mkdir -p fixtures/outputs/sprint3/ fixtures/dogfood/

# 1. fact-checker 산출물
[ -f "aiwriting/agents/aiwriting-fact-checker.md" ] || exit 1
[ -f "scripts/fact_checker.py" ] || exit 1
[ -f "known_facts.yml.example" ] || exit 1

# 2. orchestrator picker
grep -q "1.*blog" aiwriting/skills/aiwriting/SKILL.md || exit 1
grep -q "user-invocable: true" aiwriting/skills/aiwriting/SKILL.md || exit 1

# 3. portability + R6
grep -r "/Users/leesanghun" aiwriting/ && exit 1 || true
grep -rE 'R1.*R6\b' aiwriting/skills/ && exit 1 || true

# 4. all tests
pytest tests/ -q || { touch .half_scope; exit 4; }

# 5. full pipeline 16 케이스
python3 scripts/run_full_pipeline.py
[ "$(find fixtures/outputs/sprint3 -name '*.md' | wc -l | tr -d ' ')" = "16" ] || exit 6
[ "$(find fixtures/outputs/sprint3 -name '*.report.json' | wc -l | tr -d ' ')" = "16" ] || exit 6

# 6. structure-critic REJECT 0건
rejects=$(python3 -c "
import json, glob
print(sum(1 for f in glob.glob('fixtures/outputs/sprint3/*.report.json') if json.load(open(f)).get('structure_critic',{}).get('verdict') == 'REJECT'))
")
[ "$rejects" = "0" ] || { echo "REJECT count: $rejects"; exit 7; }

# 7. plugin validate 마지막
claude plugin validate aiwriting/ 2>&1 | grep -q "valid" || python3 scripts/validate_manifest.py aiwriting/.claude-plugin/plugin.json || exit 2

# 8. dogfood 4회 (Sprint 3 마지막)
bash scripts/dogfood.sh
[ "$(find fixtures/dogfood -name '*.md' | wc -l | tr -d ' ')" = "4" ] || { echo "dogfood count fail"; exit 8; }

# 9. VERIFY.sh smoke
bash VERIFY.sh

echo "sprint3 OK"
```

### 커밋
`feat(challenge-3): sprint 3 — fact-checker + orchestrator + dogfood + VERIFY`

---

## VERIFY.sh (1-command 재현, 기상 후 첫 5분)

```bash
#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
[ -d ".venv" ] || { echo "ERR: .venv missing"; exit 3; }
source .venv/bin/activate

echo "[1/10] portability gate (Critic C3)"
matches=$(grep -r "/Users/leesanghun" aiwriting/agents/ aiwriting/skills/ 2>/dev/null | wc -l | tr -d ' ')
[ "$matches" = "0" ] || { echo "  FAIL: $matches"; exit 1; }
echo "  OK"

echo "[2/10] R6→R7 migration"
r6=$(grep -rE 'R1.*R6\b' aiwriting/skills/ 2>/dev/null | wc -l | tr -d ' ')
[ "$r6" = "0" ] || { echo "  FAIL: $r6"; exit 1; }
echo "  OK"

echo "[3/10] plugin validate"
claude plugin validate aiwriting/ 2>&1 | grep -q "valid" || python3 scripts/validate_manifest.py aiwriting/.claude-plugin/plugin.json
echo "  OK"

echo "[4/10] manifest schemas"
pytest tests/test_plugin_manifest.py tests/test_marketplace_manifest.py -q
echo "  OK"

echo "[5/10] copy-killer weights = 1.0, threshold = 0.35"
pytest tests/test_copy_killer_weights.py -q
echo "  OK"

echo "[6/10] structure-critic 4 mode section"
pytest tests/test_structure_critic_modes.py -q
echo "  OK"

echo "[7/10] fact-checker 5 hard-evidence types"
pytest tests/test_fact_checker_patterns.py -q
echo "  OK"

echo "[8/10] full pipeline 16 cases (4 deterministic stages + critic replay)"
python3 scripts/run_full_pipeline.py
test "$(find fixtures/outputs/sprint3 -name '*.md' | wc -l | tr -d ' ')" = "16"
echo "  OK"

echo "[9/10] dogfood 4 outputs"
test "$(find fixtures/dogfood -name '*.md' 2>/dev/null | wc -l | tr -d ' ')" = "4" || echo "  WARN: dogfood not yet executed"

echo "[10/10] no .half_scope"
[ ! -f .half_scope ] || { cat .half_scope; exit 1; }
echo "  OK"

echo ""
echo "=== ALL GATES GREEN ==="
echo "Estimated cost: $(head -1 logs/cost_probe.txt)"
```

---

## 환경 propagation 자동 검증

Sprint 0 checkpoint 마지막 단계에서:
```bash
missing=$(grep -L 'source .venv/bin/activate' \
  scripts/checkpoint_sprint0.sh \
  scripts/checkpoint_sprint1.sh \
  scripts/checkpoint_sprint2.sh \
  scripts/checkpoint_sprint3.sh \
  VERIFY.sh 2>/dev/null | wc -l | tr -d ' ')
[ "$missing" = "0" ] || { touch .half_scope; exit 9; }
```

5 파일 모두 Sprint 0 산출물 (Critic C2 fix). Sprint 1~3은 자기 부분만 채워 넣음.

---

## prompts/session-N.txt 분배

| Session | 담당 Sprint | 모델 | max_turns |
|---------|-----------|------|-----------|
| `prompts/session-0.txt` | Sprint 0 | sonnet | 100 |
| `prompts/session-1.txt` | Sprint 1 | sonnet | 150 |
| `prompts/session-2.txt` | Sprint 2 | sonnet | 150 |
| `prompts/session-3.txt` | Sprint 3 | sonnet | 150 |

---

## 오버나이트 매핑 (밤 수 → 스프린트)

| 밤 | Sprint | 비고 |
|----|--------|-----|
| 1 | **0 + 1** | 포팅 + 4 skill + replay 라이브 녹화 1회 (~$0.53) |
| 2 | **2 + 3** | scrubber/copy-killer/fact-checker/critic + dogfood 4회 (~$0.79). 모두 LLM-free 또는 replay |

총 ~2 밤 + buffer. 5h10m × 5 retry = 26h max per session.
