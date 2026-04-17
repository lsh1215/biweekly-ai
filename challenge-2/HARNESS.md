# challenge-2 Harness

## 도구 선택

| 레이어 | 사용한 것 | 왜 |
|--------|----------|-----|
| 외부 루프 (리밋 회복) | `scripts/overnight.sh` 자체 쉘 루프 | OMC ralph도 후보였으나 본 챌린지는 3-sprint 선형 구조라 자체 루프가 더 단순. 5h10m 재시도 기본 |
| 세션 내 에이전트 | Claude Code 본체 (messages tool-use) | 이 프로젝트 자체가 "단일 agent" 구현이라 메타-레이어에서 OMC 멀티에이전트 불필요 |
| Planner 1회 선행 | `/oh-my-claudecode:ralplan` (밤 1 시작 전) | 계획-아키텍트-크리틱 합의로 Sprint 0~4 세부 잠금 |
| 검증 레인 | pytest (생성 레인과 분리) + `scripts/checkpoint_sprint*.sh` | 셀프 리뷰 금지. 코드 수정 세션과 테스트 돌리는 세션을 분리 |
| 외부 의견 2차 (선택) | 밤 3 기상 후 `/oh-my-claudecode:code-review` | VERIFY.sh 통과 이후 최종 스윕. 실패 시 회고 자료 |
| 훅 | (현재 없음) | 본 챌린지는 단순한 구조라 Hook 덧붙이면 디버깅 비용 ↑. VERIFY.sh가 실질 게이트 |

## 프롬프트 설계

### 사전 문서 (세션이 매번 읽음)
- `PRD.md` — 뭘/왜/성공기준
- `EXECUTION_PLAN.md` — 현재 스프린트 목표 + checkpoint 명령
- `TECH_STACK.md` — 기술 선택 잠금
- `~/.gstack/projects/lsh1215-biweekly-ai/leesanghun-main-design-20260418-054439.md` — 설계 근거
- `../CLAUDE.md` — 레포 8개 불변 원칙

### 세션 프롬프트 (`prompts/session-N.txt`)
- `session-0.txt` — Sprint 0 (스켈레톤 + fixture)
- `session-1.txt` — Sprint 1 (tools + RAG ingest)
- `session-2.txt` — Sprint 2 (agent loop)
- `session-3.txt` — Sprint 3 (severity + event loop)
- `session-4.txt` — Sprint 4 (VERIFY + journal)

각 세션 prompt에는:
1. 현재 스프린트 목표 (1 문단)
2. TDD 강제 명시 ("테스트 파일 먼저")
3. checkpoint 스크립트 실행 후 green 확인
4. `TIMELINE.md`에 시작/종료/결정 ISO 타임스탬프 append
5. 커밋 메시지 템플릿

### 컨텍스트 경계
- **읽음**: 위 사전 문서들 + 현재 스프린트 관련 코드
- **안 읽게**: 이전 스프린트 로그 (logs/), `.venv/`, `data/fixtures/` 원본 (tool로만 접근)
- **적극 읽음**: `TIMELINE.md` (밤 간 정보 전달의 핵심)

## 리밋 대응

### 재시도 정책
- `scripts/overnight.sh`가 외부 쉘 루프
- Claude 비인터랙티브 호출 (`claude -p`) → 로그에서 리밋 시그니처 감지 (exit code 독립적으로, Claude CLI가 exit 0으로 limit 메시지 뱉는 경우도 있음)
- 감지 시 **5시간 10분 sleep** → 재시도 (**총 최대 2회**)
- 2회 실패 시 `.half_scope`에 플래그 기록 후 종료. Downstream sprint는 자동 skip (cascade).

### Carry-over
- 특정 밤에 `.half_scope`로 막힌 스프린트는 **다음 밤의 맨 앞에 재실행**. 사용자가 플래그 파일 지운 뒤 `scripts/overnight.sh <sprint_id>`로 재투입.
- 기상한 사용자의 첫 액션 = `cat challenge-2/.half_scope` + TIMELINE 마지막 30줄 확인.

### macOS 슬립 방지 (필수)
노트북 슬립 시 sleep 카운터 멈춰서 리밋 회복 불가. 반드시:
```bash
caffeinate -di nohup bash challenge-2/scripts/overnight.sh > challenge-2/logs/overnight.out 2>&1 &
```
Linux는 `systemd-inhibit --what=sleep`.

### Checkpoint 기준 (다음 스프린트로 넘어갈 성공 조건)
- `scripts/checkpoint_sprintN.sh` exit 0
- `.half_scope` 없음
- 해당 스프린트 pytest 그린
- `git status` 클린 (스프린트 끝 = 커밋 강제)

### 세션 간 정보 전달
- `TIMELINE.md`: 세션 시작/종료, 주요 결정, 실패 이유, half-scope 플래그
- `logs/session-N-<timestamp>.log`: claude 세션 stdout (파싱하지 않음, 회고용)
- git 커밋 히스토리: 각 스프린트 단위 1 커밋 롤백 보장

## 실측 결과 (회고 때 채움)

- 리밋 발동 횟수:
- 자동 재개 성공률:
- 사람 개입 필요했던 지점:
- Sprint별 소요 세션 수 (목표 = 1 세션/스프린트):
- 총 Claude 비용 실측 (예산 $50 대비):
- 다음 챌린지에 가져갈 것:
- 다음 챌린지에 버릴 것:

## 사전 체크리스트 (밤 1 시작 전)

- [ ] Design doc APPROVED 상태 확인 (완료)
- [ ] Anthropic API 키 `export ANTHROPIC_API_KEY=...` (overnight.sh preflight 체크)
- [ ] Docker 데몬 실행 중 (overnight.sh preflight 체크)
- [ ] `git status` 클린
- [ ] `scripts/overnight.sh` 실행 권한 (`chmod +x`)
- [ ] `.half_scope` 파일 없음 (`rm -f challenge-2/.half_scope` 필요 시)
- [ ] 슬립 방지: **macOS는 `caffeinate -di nohup bash ... &` 필수**
- [ ] ralplan 합의 완료 (REJECT → revision 2까지 수정 반영)
