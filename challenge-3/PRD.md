# challenge-3 PRD — aiwriting Claude Code Plugin

**Status**: v3 (post-Critic). Architect Critical 3 + Synthesis 5 + Major 4 + Critic Critical 3 + Major 5 + Pre-mortem 9 시나리오 모두 lock.
**기간**: 2026-04-29 ~ 2026-04-30 overnight 랄프톤
**예산**: $7.50 (정적 추정 $1.50 + dogfood 4회 $0.26 + retry buffer 2회 $2.11 + safety margin)

---

## 1. 한 줄 요약

사용자 `~/.claude/skills/blog/` + `~/.claude/agents/{blog-writer, ai-tell-scrubber, blog-critic}.md` 자산을 portable Claude Code plugin (`aiwriting`)으로 포팅·일반화한다. blog 외 3개 포맷(cover-letter / paper / letter) 추가. 산출물은 `claude plugin validate` 통과 + marketplace 배포 가능 단위.

## 2. 왜 / 무엇을 / 비-목표

### 2.1 Why
- 사용자 자산이 `~/.claude/`에 묶여 portable 0%. 다른 머신·다른 사용자에 이전 불가.
- 1 포맷(blog)에만 묶여 자기소개서·논문·편지 작성 시 매번 ad-hoc.
- AI tell 제거 R1~R7 자산이 blog만 cover. 다른 포맷에 미적용.

### 2.2 What
- `aiwriting` 플러그인 (`challenge-3/aiwriting/`) — 5 agents + 5 skills + manifest.
- Sprint 0~3 (4개) overnight 자율 실행.
- 16 fixture (4 format × 4 topic) deterministic full pipeline E2E.
- dogfood 4회 (4 format × 1 topic) 라이브 산출.

### 2.3 Non-goals
- 외부 AI detector(GPTZero 등) API 호출. copy-killer는 **내부 pure function only**.
- 한국어 외 다국어.
- Notion 무조건 의존. Notion MCP 미존재 시 graceful skip (D4).
- 사용자 `~/.claude/*` 자산 직접 수정. 우리는 fork(복사) + path rewrite만.
- AI dispatch routing. 사용자가 numeric picker로 직접 선택 (SYNTH-2).
- v1에서 marketplace publish. install validate까지만.

## 3. 핵심 결정 (모두 LOCKED)

### D1 — Universal writer 1개 (4 포맷 분기)
- 단일 agent: `aiwriting-writer.md` (model: sonnet).
- format param: `blog | cover-letter | paper | letter`.
- format별 knowledge file 세트 (asymmetry는 의도 — blog 가장 성숙, letter 가장 simple):
  - blog: 5 file (philosophy/style-rules/templates/argumentation/ai-tell-rules)
  - cover-letter: 2 file (philosophy/cover-letter-templates)
  - paper: 3 file (philosophy/argumentation/paper-templates)
  - letter: 1 file (letter-templates)
- agent 본문 ≤200 라인 예산. 초과 시 challenge-4에서 분리.

### D2 — 5 agents (디렉토리 채택)
1. `aiwriting-writer.md` (sonnet) — universal writer
2. `aiwriting-scrubber.md` (sonnet) — R1~R7 deterministic grep gate
3. `aiwriting-copy-killer.md` (**LLM-free pure function**) — 6 지표 score + threshold
4. `aiwriting-structure-critic.md` (opus, 단일 .md + 4 mode section) — 논증 평가
5. `aiwriting-fact-checker.md` (**LLM-free pure function**) — 5 type pattern

**Critic C1 fix**: copy-killer + fact-checker는 LLM 호출 0회. Python regex + 가중치 score만. → 16 fixture pipeline 중 4 stage(writer/scrubber/copy-killer/fact-checker) deterministic. critic 1 stage만 LLM, 별도 replay 단위 테스트로 결정성 보장.

### D3 — fact-checker 5 hard-evidence type (LLM-free regex)
사용자 yaml `known_facts.yml` 외에 한해서만 BLOCK:
- (a) 숫자: `\b\d+(\.\d+)?\b`, `\b\d+(\.\d+)?%\b`, `[\$₩€]\d+(\.\d+)?[KMB]?\b`
- (b) semver: `\bv?\d+\.\d+\.\d+([.-][a-z0-9]+)*\b`
- (c) 직접 인용: `"[^"]{8,}"`, `「[^」]{8,}」`
- (d) 날짜: `\b\d{4}\b`, `\b\d{4}-\d{2}\b`, `\b\d{4}-\d{2}-\d{2}\b`
- (e) 고유명사: 사용자 yaml의 `proper_nouns_known: [...]` list 외 KSS-탐지 (또는 hand-pattern)

WARNING(BLOCK 아님): 동의어, 서술형, 일반 형용사. dogfood 검토 권장만.

### D4 — Notion publish graceful skip
blog skill Phase 5 첫 줄에 `if Notion MCP unavailable: notice "saved locally" + return success`. 기존 blog 워크플로우 회귀 0건.

### D5 — `.venv` FORCED (silent skip 금지)
- Sprint 0 진입 첫 명령: `python3 -m venv challenge-3/.venv`.
- 모든 `checkpoint_sprintN.sh`와 `VERIFY.sh` 첫 3 라인:
  ```bash
  set -euo pipefail
  cd "$(dirname "$0")/.."
  [ -d ".venv" ] || { echo "ERR: .venv missing (D5 violation)"; exit 3; }
  source .venv/bin/activate
  ```
- 미존재 시 즉시 fail with exit 3.

### D6 — copy-killer 6 지표 + threshold (LLM-free)

| Indicator | Weight | 계산 |
|-----------|--------|-----|
| sentence_length_variance | 0.20 | std/mean of sentence char length |
| avg_syllable_length | 0.10 | mean Hangul syllable count per 100 chars |
| connector_frequency | 0.20 | 그러나/하지만/따라서/즉/또한 per 1000 chars |
| r1_r7_residual | 0.30 | scrubber 후 R1~R7 grep 매치 수 |
| monotone_ending_ratio | 0.15 | 4문장 연속 동일 어미 발생 횟수 / 총 문장 수 |
| generic_modifier_density | 0.05 | 매우/정말/너무/굉장히 per 1000 chars |
| **합계** | **1.00** | |

- threshold default = 0.35. `ai_score > threshold` → BLOCKED.
- **결정 룰** (Critic S3 fix): Sprint 2 첫 16 fixture 분포 측정 후 fail 비율 > 50%면 threshold ±0.05 단위 1회 자동 조정 (0.30~0.45 범위). 그래도 fail > 50%면 6 지표 weight를 균등 1/6=0.167로 reset (deterministic, LLM 판단 없음). TIMELINE에 모든 변경 기록.
- 외부 detector 통과 보장 X. 내부 정량 신호 only. README에 한계 명시.

### D7 — replay JSON shape 7 key + dispatch_key sha256
```json
{
  "model": "claude-sonnet-4-5",
  "captured_at": "2026-04-29T03:00:00Z",
  "stage": "writer | structure-critic",
  "request": { "system": "...", "messages": [...], "tools": [...] },
  "response": { "stop_reason": "end_turn", "content": [...] },
  "dispatch_key": "<sha256 utf8(request.messages[*].content text concat \\n)>",
  "format": "blog | cover-letter | paper | letter"
}
```
- 매칭: dispatch_key 정확 일치만.
- prompt 변경 시 fixture stale → overnight 자동 재녹화 **금지**.
- **Critic Major 3 fix**: stale 감지 시 cascade rule lock — `.half_scope=replay_stale_sprintN` 발동 → 해당 sprint abort + downstream sprint cascade skip + RETRO에 `replay_stale at sprint N` 명시.

### D8 — Sprint 4개 (0/1/2/3)

### D9 — Direct slash 4개 + numeric picker (no AI dispatch)
- `/aiwriting:blog`, `/aiwriting:cover-letter`, `/aiwriting:paper`, `/aiwriting:letter` 직접 진입 (`user-invocable: true`).
- `/aiwriting` orchestrator는 1줄 numeric picker만:
  ```
  어떤 글을 쓸까요?
  1. blog  2. cover-letter  3. paper  4. letter
  번호 입력 → 해당 직접 슬래시로 redirect.
  ```
- AI dispatch 0%.

### D10 — 16 fixture topic lock (Critic Major 4 fix)
| Format | Topic 1 | Topic 2 | Topic 3 | Topic 4 |
|--------|---------|---------|---------|---------|
| blog | "Kafka exactly-once semantics" | "Resilience4j circuit breaker tuning" | "PostgreSQL UPSERT vs MERGE" | "Python 3.13 GIL removal impact" |
| cover-letter | "Backend engineer @ fintech (3년차)" | "ML engineer @ AI startup (신입)" | "DevOps engineer @ 대기업 (5년차)" | "Frontend engineer @ scale-up (2년차)" |
| paper | "Empirical study of LLM hallucination in code generation" | "Cost-aware retrieval-augmented generation" | "Adversarial robustness of vision transformers" | "Federated learning convergence under non-IID data" |
| letter | "감사 편지 (전 직장 멘토)" | "축하 메시지 (친구 결혼)" | "위로 편지 (지인 부친상)" | "추천서 (대학원 진학 학생)" |

각 fixture는 `challenge-3/fixtures/inputs/{format}/{slug}.yml` 형식. content는 토픽 + 사용자 사실 + 톤 옵션 lock.

### D11 — 4 stage deterministic + 1 stage LLM-replay (Critic C1 fix)
| Stage | Type | 결정성 |
|-------|------|-------|
| writer | LLM (sonnet) | replay-driven |
| scrubber | LLM (sonnet) deterministic grep | grep gate가 deterministic |
| copy-killer | **Pure Python** (regex + score) | 100% deterministic |
| fact-checker | **Pure Python** (regex pattern) | 100% deterministic |
| structure-critic | LLM (opus) | replay-driven (단위 테스트만) |

16 fixture full pipeline은 writer-replay → scrubber → copy-killer → fact-checker 4 stage만 통과 검증. structure-critic은 별도 replay 단위 테스트(4 mode × 4 fixture 입력 → APPROVE/ITERATE/REJECT verdict 결정성 lock).

### D12 — dogfood 4회 (Critic Major 5 fix)
4 format × 1 topic = 4 dogfood. Sprint 3 마지막 단계 + 사용자 깨어난 후 evidence.

## 4. Plugin 디렉토리 레이아웃

```
challenge-3/aiwriting/                   # plugin root (validate 대상)
├── .claude-plugin/
│   ├── plugin.json                      # metadata 4 필드
│   └── marketplace.json                 # source: "./"
├── README.md                            # 한계 명시
├── LICENSE                              # MIT, Copyright (c) 2026 Sanghun Lee
├── agents/
│   ├── aiwriting-writer.md              # sonnet
│   ├── aiwriting-scrubber.md            # sonnet
│   ├── aiwriting-copy-killer.md         # LLM-free
│   ├── aiwriting-structure-critic.md    # opus, 단일 .md + 4 mode
│   └── aiwriting-fact-checker.md        # LLM-free
└── skills/
    ├── aiwriting/                       # orchestrator (numeric picker)
    │   └── SKILL.md
    ├── blog/                            # user-invocable
    │   ├── SKILL.md
    │   ├── philosophy.md
    │   ├── style-rules.md
    │   ├── templates.md
    │   ├── argumentation.md
    │   └── ai-tell-rules.md             # R1~R7
    ├── cover-letter/
    │   ├── SKILL.md
    │   ├── philosophy.md
    │   └── cover-letter-templates.md
    ├── paper/
    │   ├── SKILL.md
    │   ├── philosophy.md
    │   ├── argumentation.md
    │   └── paper-templates.md
    └── letter/
        ├── SKILL.md
        └── letter-templates.md
```

### plugin.json (metadata-only 4 필드)
```json
{
  "name": "aiwriting",
  "version": "0.1.0",
  "description": "Korean writing pipeline plugin: writer → scrubber → copy-killer → critic → fact-checker for blog/cover-letter/paper/letter.",
  "author": {
    "name": "Sanghun Lee",
    "email": "vitash1215@gmail.com"
  }
}
```

### marketplace.json
```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "aiwriting",
  "description": "Korean multi-format writing pipeline",
  "owner": { "name": "Sanghun Lee", "email": "vitash1215@gmail.com" },
  "plugins": [
    {
      "name": "aiwriting",
      "description": "writer/scrubber/copy-killer/structure-critic/fact-checker, 4 formats",
      "version": "0.1.0",
      "source": "./",
      "category": "productivity"
    }
  ],
  "version": "0.1.0"
}
```

## 5. 성공 기준 (VERIFY.sh hard gates, 모두 0 fail)

1. `claude plugin validate challenge-3/aiwriting/` 또는 jsonschema fallback 통과
2. `grep -r "/Users/leesanghun" challenge-3/aiwriting/agents/ challenge-3/aiwriting/skills/` → 0 matches (C3 portability)
3. `grep -rE 'R1.*R6\b' challenge-3/aiwriting/skills/` → 0 matches (C3 R6→R7)
4. `pytest challenge-3/tests/ -q` 전부 pass
5. 16 fixture × 4 deterministic stage(writer-replay/scrubber/copy-killer/fact-checker) 통과 + 산출물 .md 16개 + .report.json 16개 생성
6. `.half_scope` 부재
7. cost ledger `logs/cost_probe.txt` 첫 줄 `estimated_total_usd=` 형식이며 값 ≤ $7.50
8. `challenge-3/aiwriting/marketplace.json` schema 통과
9. structure-critic replay 단위 테스트 (4 mode × 4 input = 16 verdict) deterministic
10. dogfood 4회 산출물 존재 (`fixtures/dogfood/{format}.md` 4개) — sprint 3 마지막

Soft gates (TIMELINE 기록만):
- copy-killer 16 fixture 중 ≥12 PASS (≥75%)
- structure-critic APPROVE 비율 ≥50%
- 모든 산출물 Hangul ratio ≥0.7 (S6 fix)

## 6. Pre-mortem (9 시나리오, lock)

| ID | 트리거 감지 | 대응 |
|----|-----------|------|
| S1 | `claude plugin validate` 명령 미존재 (`command not found`) | jsonschema fallback (`scripts/validate_manifest.py`). schema URL fetch 실패 시 cached schema 사용. 둘 다 실패 시 `.half_scope=schema_unavailable` |
| S2 | knowledge file plugin-relative reference ambiguity | Sprint 0에서 `${CLAUDE_PLUGIN_ROOT}` env var spec 재확인. 미지원 시 agent .md에 명시 "Read tool로 cwd 기준 상대 경로 로드" |
| S3 | copy-killer threshold 0.35로 16 fixture fail > 50% | D6 자동 튜닝 ±0.05 1회. 그래도 fail > 50%면 weight 균등 1/6 reset (LLM 판단 없음, deterministic 룰) |
| S4 | Sprint 1 라이브 녹화 ANTHROPIC_API_KEY fail (401/keychain) | hand-authored fixture 폴백 (4 format × 1 topic = 4 hand-authored — 16 전체는 비현실, dogfood 시점에 사용자 보강) + `.half_scope=api_key_fail` 부분 abort |
| S5 | macOS keychain locked (`claude` CLI auth fail) | `.half_scope=auth_locked` + Sprint 1 라이브 녹화 abort. Sprint 0/2/3 (LLM-free)는 진행 |
| S6 | Sprint 1 녹화 산출물 Hangul ratio < 0.7 (영어 leak) | `.half_scope=lang_leak_<format>` + 해당 fixture만 hand-author로 대체 |
| S7 | plugin.json schema URL fetch 실패 | local cached schema (Sprint 0 진입 시 1회 fetch + commit) 사용. 미캐시면 `.half_scope=schema_unavailable` |
| S8 | dogfood 산출물이 사용자가 봐도 못 쓴 글 | 무인 실행 검증 불가. 기상 후 사용자 평가. RETRO `dogfood 사용자 평가` 섹션 |
| S9 | 16 fixture stage간 partial file (race condition) | checkpoint 진입 시 `rm -rf fixtures/outputs/sprint${N}/` 멱등화 (CLAUDE.md §10) |

추가:
- **`pip install` 네트워크 차단**: `.half_scope=pip_offline` + scrubber/copy-killer는 stdlib `re` only로 동작. PRD §12 기본값.
- **`replay_stale` cascade**: 발생 sprint abort + downstream sprint cascade skip (D7 lock).

## 7. 환경 변경 propagation 체크리스트

CLAUDE.md §9 강제. Sprint 0 결정이 Sprint 1~3 + VERIFY.sh에 같은 세션 안 반영:

| 변경 | Sprint 0 | Sprint 1 | Sprint 2 | Sprint 3 | VERIFY.sh |
|-----|---------|---------|---------|---------|----------|
| `.venv` activate | ✓ | ✓ | ✓ | ✓ | ✓ |
| `[ -d .venv ] \|\| exit 3` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `cd "$(dirname "$0")/.."` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `set -euo pipefail` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `grep "/Users/leesanghun" → 0` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `grep -rE 'R1.*R6\b' → 0` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `docker-compose` (하이픈) 0건 | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ANTHROPIC_API_KEY` hard-check 부재 | ✓ | ✓ | ✓ | ✓ | ✓ |

**Critic C2 fix**: Sprint 0 산출물에 `checkpoint_sprint{0,1,2,3}.sh` + `VERIFY.sh` skeleton 4 + 1 = **5개 파일 모두 한 번에 생성**. 위 propagation 블록을 5 파일 모두 첫 4 라인에 박은 채로 출발. Sprint 1~3는 자기 부분만 채워 나감. Sprint 0 끝 자동 검증:
```bash
missing=$(grep -L 'source .venv/bin/activate' scripts/checkpoint_sprint*.sh VERIFY.sh | wc -l)
[ "$missing" -eq 0 ] || { touch .half_scope; exit 9; }
```

## 8. 비용 추정 (LLM 호출 정적 계산)

- Sprint 1 라이브 녹화: 4 format × (writer 1 + structure-critic 1) = 8 호출 × 평균 ($3 in × 2k + $15 out × 4k) / 1M = 8 × $0.066 = **$0.53**
- 16 fixture replay: 0회 라이브 (전부 fixture)
- dogfood 4회: 4 × $0.066 = **$0.26**
- Sprint 0~3 cost_probe: 0회 라이브 (정적 추정만, M5)
- retry buffer 2회: $0.53 × 2 = **$1.06**
- safety margin: **$5.65**

총 cap: **$7.50**. cost_probe.py 산출 첫 줄 `estimated_total_usd=` 값이 이 cap 이하여야 hard gate 7 통과.

## 9. 비협상 사항 (요약)

- plugin.json metadata-only 4 필드 (C1)
- `claude plugin validate` + jsonschema fallback (C2)
- `grep "/Users/leesanghun" → 0` (C3)
- `grep -rE 'R1.*R6\b' → 0` (Critic C3)
- `.venv` FORCED (D5)
- replay 자동 재녹화 금지, stale cascade rule lock (D7)
- copy-killer / fact-checker LLM-free (Critic C1)
- 16 fixture topic lock (D10)
- dogfood 4회 (D12)
- structure-critic replay 단위 테스트 (D11)
- 9 pre-mortem 시나리오 lock

## 10. 참조

- `../CLAUDE.md` (12 원칙)
- `../HARNESS.md` (lane separation §1.3)
- `../PLAYBOOK.md` (overnight 프로토콜)
- `../challenge-2/RETRO.md` (cascade fail 4 사례 → D5/D7/M5 직접 반영)
- 포팅 원본: `~/.claude/skills/blog/`, `~/.claude/agents/blog-*.md`
- 플러그인 spec: `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/example-plugin/.claude-plugin/plugin.json`
