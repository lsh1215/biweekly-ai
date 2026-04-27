# challenge-3 HARNESS — 도구·훅·스킬 선택 기록

이 챌린지에서 어떤 하네스 도구를 왜 골랐는지의 audit trail. RIA(challenge-2) 회고 결과 직접 반영.

## 도구 카탈로그

### Claude Code 기본 도구
| 도구 | 사용처 | 이유 |
|------|------|------|
| `Read`, `Write`, `Edit` | 모든 파일 작업 | 표준 |
| `Glob`, `Grep` | portability/R6 검증 | grep gate가 결정성 핵심 |
| `Bash` | checkpoint·VERIFY 실행 | shell loop 중심 |
| `TaskCreate/Update` | 스프린트 추적 | overnight 자율 실행 progress 가시화 |

### 외부 의존 (최소)
| 도구 | 사용처 | 이유 |
|------|------|------|
| `python3` (system default 3.13) | scripts/, tests/ | .venv 격리 |
| `pytest` | TDD 강제 | CLAUDE.md §2 |
| `pyyaml` | manifest/fixture 파싱 | 표준 |
| `regex` Python lib (PyPI) | 한글 음절 카운트 | stdlib re가 한글 정밀도 부족 |
| `claude` CLI | Sprint 1 라이브 녹화 1회만 | 그 외 호출 0 |

### 사용 안 함 (의도적 배제)
- Docker / docker compose: 본 챌린지 DB 없음. RIA의 docker compose v2 이슈 회피.
- Postgres / pgvector: 데이터 저장 없음.
- GPU / MPS: 로컬 LLM 미사용.
- 외부 AI detector API (GPTZero, Originality.ai 등): copy-killer는 내부 pure function only.
- Notion MCP: blog Phase 5 graceful skip guard 적용 (D4).
- WebSearch/WebFetch in agent runtime: replay fixture로 우회.

## 훅 (hooks)

### 미사용
이 챌린지는 settings.json hooks 미사용. 이유:
- Sprint 진입/종료는 외부 쉘(`overnight.sh`)이 통제.
- TIMELINE.md append는 session 프롬프트가 직접.
- Hook 추가 시 디버깅 표면 증가, 결정성 저하.

## 스킬 (skills)

### 직접 사용
- `/oh-my-claudecode:planner`, `architect`, `critic` (모두 opus) — 사전 ralplan 합의 (Architect Critical 3 + Synthesis 5 + Critic Critical 3 도출)
- `/loop 10m` 또는 `CronCreate` — 사용자 자는 동안 진행 모니터링 (선택, 기본 사용 안 함 — TIMELINE.md tail이면 충분)

### 사용 안 함
- `/oh-my-claudecode:ralph` — 자율 self-replicating loop 강력하지만 본 챌린지는 sprint 4개로 단순 → overnight.sh shell loop 충분
- `/oh-my-claudecode:autopilot` — over-engineering
- `/oh-my-claudecode:ultrawork`, `team` — 병렬 agent 필요 없음 (sprint sequential)

## 패턴 결정

### Replay-first (RIA의 Hand-authored 변형)
RIA(challenge-2)는 yfinance/SEC 외부 호출을 fixture-first로 처리. challenge-3은 다음:
- Sprint 1에서 writer + structure-critic 라이브 녹화 1회 (32 호출, ~$2.10)
- 이후 모든 호출은 dispatch_key sha256 매칭 replay
- copy-killer + fact-checker는 LLM 호출 0회 (pure function — Critic C1 fix)

**왜 hand-authored가 아닌 라이브 녹화인가**: 글쓰기 자유 텍스트는 hand-author 비용 100배 (4 format × 4 topic × 평균 1k 단어 = 16k 단어). 라이브 1회로 cost-effective.

**Replay stale 시**: 자동 재녹화 금지 (D7). `.half_scope=replay_stale_sprintN` flag만 발동, 사용자 수동 `recapture_replay.sh` 발동 필요.

### .venv FORCED (RIA §9 직접 fix)
RIA Sprint 0 .venv propagation 누락 cascade fail 재발 방지:
- Sprint 0가 5 파일 (`checkpoint_sprint{0,1,2,3}.sh` + `VERIFY.sh`) 모두 한 번에 생성 + 첫 4 라인에 `.venv` 활성화 박힘
- Sprint 0 끝 자동 검증: `grep -L 'source .venv/bin/activate' ... | wc -l` == 0
- silent skip 금지, exit 3

### Checkpoint 멱등성 (RIA §10 직접 fix)
- 모든 checkpoint 진입 시 `rm -rf fixtures/outputs/sprint${N}/` 먼저
- replay fixture는 보존 (Sprint 1 산출물, deterministic 입력)
- DB 없음 → TRUNCATE 불필요
- `.half_scope` 존재 시 cascade skip (downstream sprint 진입 즉시 exit 0)

### `claude plugin validate` + jsonschema fallback
S1 시나리오 — 명령 미존재 가능성. 2단 폴백:
1. `claude plugin validate aiwriting/`
2. `python3 scripts/validate_manifest.py aiwriting/.claude-plugin/plugin.json` (jsonschema lib + cached schema)
3. 둘 다 실패 → `.half_scope=schema_unavailable`

### docker compose 사용 안 함
RIA §11 v2 문법 이슈는 본 챌린지엔 무관. 단, 모든 .sh에 `docker-compose` (하이픈) grep gate 박음 (혹시 미래 변경 시 즉시 발견).

### API 키 hard-check 금지 (RIA §12)
- `cost_probe.py`는 `claude --version`만 (라이브 호출 0회)
- `claude -p "ping"` preflight 금지 (불필요한 비용)
- ANTHROPIC_API_KEY env var 검사 금지 — keychain 인증 fallback에 의존
- Sprint 1 라이브 녹화 시점에만 실제 호출 → 실패 시 `.half_scope=auth_locked` (S5)

## 챌린지별 기록

### 결정성 보장 architecture (Critic C1 fix)
| Stage | LLM? | 결정성 메커니즘 |
|-------|------|---------------|
| writer | ✓ (sonnet) | replay (dispatch_key sha256) |
| scrubber | ✓ (sonnet) | replay + grep gate |
| copy-killer | ✗ (pure Python) | regex + 가중치 score |
| fact-checker | ✗ (pure Python) | regex + yaml diff |
| structure-critic | ✓ (opus) | replay (별도 단위 테스트) |

16 fixture full pipeline 통과 검증 = 4 deterministic stage (writer-replay/scrubber/copy-killer/fact-checker). structure-critic은 별도 4 mode × 4 input = 16 verdict 결정성 단위 테스트.

### Pre-mortem 9 시나리오 (PRD §6)
S1~S9 모두 trigger 감지 + 대응 lock. challenge-2는 4 시나리오만 회고에서 발견 — challenge-3은 사전 9개 lock으로 cascade fail risk 줄임.

### dogfood 4회 (사용자 깨어난 후 검증용)
Sprint 3 마지막 단계 또는 사용자 깨어난 후 1회. 4 format × 1 topic = 4 라이브 산출. RETRO `dogfood 사용자 평가` 섹션에서 사용자가 직접 봐서 평가.
