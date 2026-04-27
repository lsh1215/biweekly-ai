# challenge-3 VERIFY — 1-command 재현 절차

기상 후 첫 5분 안에 결과 재현 가능. 한 명령:

```bash
cd /Users/leesanghun/My_Project/agent-engineering/biweekly-ai/challenge-3
bash VERIFY.sh
```

## 사전 조건
- macOS 14+ 또는 Linux
- Python 3.13 (system default)
- `claude` CLI (선택 — `claude plugin validate` 사용 시)
- 인터넷 연결 (jsonschema spec fetch 시)

## VERIFY.sh가 검증하는 10 gate

| # | Gate | 통과 조건 |
|---|------|---------|
| 1 | portability | `grep "/Users/leesanghun" → 0 matches` |
| 2 | R6→R7 migration | `grep -rE 'R1.*R6\b' → 0 matches` |
| 3 | plugin validate | `claude plugin validate aiwriting/` 또는 jsonschema fallback 통과 |
| 4 | manifest schemas | `pytest test_plugin_manifest.py test_marketplace_manifest.py` |
| 5 | copy-killer 가중치 | `pytest test_copy_killer_weights.py` (합 1.0, threshold 0.35) |
| 6 | structure-critic 4 mode | `pytest test_structure_critic_modes.py` |
| 7 | fact-checker 5 type | `pytest test_fact_checker_patterns.py` |
| 8 | full pipeline 16 cases | `python scripts/run_full_pipeline.py` → 16 .md + 16 .report.json |
| 9 | dogfood 4 outputs | `fixtures/dogfood/{format}.md` 4개 (warning if absent) |
| 10 | no .half_scope | `[ ! -f .half_scope ]` |

## 실패 시 진단

```bash
# 1. .half_scope 확인
cat challenge-3/.half_scope 2>/dev/null

# 2. 마지막 sprint 로그
tail -100 challenge-3/logs/sprint*.attempt*.log

# 3. TIMELINE 마지막 30 줄
tail -30 challenge-3/TIMELINE.md

# 4. 어느 gate에서 실패?
bash challenge-3/VERIFY.sh
# 출력에서 "FAIL" 첫 줄 확인
```

## 추가 검증 (선택)

### Plugin install dogfood
```bash
# 1. plugin install
claude plugin install ~/My_Project/agent-engineering/biweekly-ai/challenge-3/aiwriting --local

# 2. 슬래시 호출
claude -p "/aiwriting:blog Kafka exactly-once semantics"

# 3. 결과 검증
ls fixtures/dogfood/
cat fixtures/dogfood/blog.md
```

### Cost ledger
```bash
head challenge-3/logs/cost_probe.txt
# estimated_total_usd=X.XX (≤ $7.50)

# 실제 사용량 (라이브 녹화 + dogfood)
grep -E '\$[0-9]' challenge-3/logs/sprint*.log | tail -10
```

## 산출물 위치

```
challenge-3/
├── PRD.md                              # v3 락 결정
├── EXECUTION_PLAN.md                   # Sprint 0~3
├── HARNESS.md                          # 도구 선택 audit
├── TECH_STACK.md                       # 의존성
├── VERIFY.md                           # 본 파일
├── VERIFY.sh                           # 1-command 검증
├── TIMELINE.md                         # 실시간 audit trail
├── RETRO.md                            # 회고 (Sprint 3 후 작성)
├── known_facts.yml.example             # 사용자 yaml 템플릿
├── requirements.txt
├── .venv/                              # FORCED
├── aiwriting/                          # plugin (validate 대상)
│   ├── .claude-plugin/{plugin,marketplace}.json
│   ├── README.md, LICENSE
│   ├── agents/aiwriting-{writer,scrubber,copy-killer,structure-critic,fact-checker}.md
│   └── skills/{aiwriting,blog,cover-letter,paper,letter}/
├── fixtures/
│   ├── inputs/{format}/*.yml           # 16
│   ├── outputs/sprint{0..3}/*.{md,report.json}
│   └── dogfood/{format}.md             # 4
├── replay/fixtures/{format}/*.json     # writer + critic replay
├── prompts/session-{0..3}.txt
├── scripts/
│   ├── overnight.sh
│   ├── checkpoint_sprint{0..3}.sh
│   ├── cost_probe.py
│   ├── validate_manifest.py
│   ├── copy_killer.py
│   ├── fact_checker.py
│   ├── run_full_pipeline.py
│   ├── recapture_replay.sh
│   └── dogfood.sh
├── tests/
│   └── test_*.py                       # 11+ unit + 4 integration
└── logs/
    └── *.log, cost_probe.txt
```
