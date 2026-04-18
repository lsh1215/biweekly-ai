# Challenge-2 Retrospective — Reactive Investment Agent (RIA)

**기간**: 2026-04-17 ~ 2026-04-18 (오버나이트 랄프톤)
**주제**: 한국 거주 서학개미 중급자용 포트폴리오 관리 에이전트 (Claude SDK + pgvector + agentic RAG + 이벤트 interrupt)
**결과**: Sprint 0~4 완료, VERIFY.sh **10/10 green**, **116 tests pass**, **$0.50 / $50 예산** 사용

---

## 진행 타임라인

자기 전 ~5시간 (PO review + ralplan + 스캐폴딩) → 오버나이트 자율 실행 → 기상 후 VERIFY.sh.

| Sprint | 커밋 | 소요 | 비고 |
|--------|------|-----|------|
| 0 scaffold + fixtures + cost probe | `9df7ee1` | ~15분 | 공시 7개 실파일 확보 (SEC User-Agent 자체 교정) |
| 1 tools + pgvector ingest | `d2c7e51` | ~12분 | 686 filings_chunks, MiniLM 다국어 한계 명시 |
| 2 agent loop + replay | `5115970` + 복구 `e5f84fc` | ~11분 (half_scope 1회) | Hand-authored replay fixture (no API key) |
| 3 severity + interrupt (P0-only) | `a1d0f70` + 복구 `cdb9cdd` | ~10분 (self-heal 1회) | VCR-driven Haiku classify |
| 4 journal + cost_summary + VERIFY | `e89768e` | ~15분 | VERIFY.sh 10/10 첫 시도 통과 |

**총 경과**: 약 3시간 15분. self-heal 3회 포함. 사용자 개입 1회 (.venv propagation 누락 패치 후 재launch).

---

## 잘된 점 (재사용할 패턴)

- **`/office-hours` → `/oh-my-claudecode:ralplan` 순차 적용**: PO-level forcing questions + adversarial critic으로 **23개 이슈 (Critical 6 + Major 12 + Minor 5)를 착수 전 사전 해소**. challenge-1엔 없던 단계. 확실히 값어치 있었음.
- **Fixture-first 전략**: yfinance·Yahoo RSS·SEC EDGAR 세 외부 소스를 Sprint 0에서 한 번만 다운로드 후 커밋 → **런타임 네트워크 의존 제로**. 오버나이트 중 외부 장애 영향 없음.
- **Hand-authored / VCR replay**: ANTHROPIC_API_KEY가 없는 상태에서 overnight Claude가 "라이브 호출 대신 synthetic replay JSON으로 결정론 확보" 자체 결정 → Sprint 2/3 모두 API 키 0회 호출로 통과. 이 패턴이 랄프톤의 새 표준.
- **`/loop 10m` + CronCreate 모니터링**: 사용자가 자는 동안 내가(메인 Claude) 10분 주기로 TIMELINE diff·sprint 로그·half_scope·git log를 채팅창에 자동 push. 깨어나서 10분치 히스토리로 밤 사이 상황 즉시 파악. challenge-1엔 없던 UX 개선.
- **Claude 자율 self-heal 3회 실증**:
  1. SEC EDGAR User-Agent 403 → email 형식으로 자체 교정
  2. checkpoint_sprint3 event_cooldown 비멱등 → 2-line TRUNCATE 패치 자체 commit
  3. `sprint-2 DONE` idempotent no-op 판단 (재작업 없이 TIMELINE 로그만)
- **커밋 컨벤션**: feat/fix/docs 접두 + scope `(challenge-2)` + 짧은 설명. 13개 커밋 전부 일관. 롤백·조회 용이.
- **비용 projection vs actual 잘 맞음**: Sprint 0 cost_probe 추정 $0.53 → 실측 $0.50. replay 덕에 LLM 라이브 호출 최소화.

---

## 문제점

- **`.venv` activation propagation 누락** (치명): Sprint 0 오버나이트 세션이 homebrew PEP 668 회피로 `.venv`를 만들고 `checkpoint_sprint0.sh`, `checkpoint_sprint1.sh`에 `source .venv/bin/activate` 블록 추가. 그런데 **2/3/4에 전파 안 함**. Sprint 2 외부 checkpoint가 venv 밖에서 pytest 실행하다 fail → 2회 재시도 모두 fail → `.half_scope`=sprint-2 → **OVERNIGHT_RUN ABORT**. 사용자 깨서 내가 수동 패치 후 재launch.
- **Checkpoint 비멱등성**: `checkpoint_sprint3.sh`가 `process-events`를 부르는데, 이전 실행에서 `event_cooldown` 테이블에 남은 entries 때문에 P0 이벤트가 cooldown_skip 당해 interrupt 파일 생성 안 됨 → checkpoint fail. Overnight Claude가 원인 진단하고 `TRUNCATE event_cooldown` 2줄 추가로 자체 수리.
- **`docker-compose` v1 → v2 전환**: 최근 Docker Desktop은 v1 binary 제거. `docker-compose` (하이픈) 사용하는 스크립트는 command not found. Sprint 0 세션이 `checkpoint_sprint0/1` 은 자체 교정했으나 2/3/4/VERIFY.sh는 내가 수동 교정.
- **pip install -e . 재설치 console script 일시 깨짐**: `ria` 엔트리포인트 스크립트가 첫 VERIFY.sh 실행 때 "No such file or directory"로 실패. 원인은 venv bin 쪽 stale metadata. 수동 재설치 후 정상. 재현성 있는지 미검증.
- **ANTHROPIC_API_KEY preflight 오작동**: 내가 overnight.sh에 `[ -n "$ANTHROPIC_API_KEY" ]` hard-check 박았는데, Claude Code는 보통 keychain 인증 사용 → env var 없어도 `claude -p` 작동. Preflight가 너무 strict해서 오버나이트 중 `PRECHECK_FAIL`로 cascade abort 위험 있었음. 다행히 claude subprocess들이 "env var 없지만 local-decidable work" 판단으로 우회.

---

## 아쉬운 점

- **Sprint 2 half_scope → 사용자 1회 개입** 필요했음. 완전 무인 실행 목표에서 뒷걸음질. 원인이 설계자(나)의 "Sprint 0 변경이 downstream에 자동 전파되지 않는 구조"여서, overnight Claude 탓 아님. 설계 단계에서 더 꼼꼼히 봤어야.
- **macOS `caffeinate` 주입을 내가 overnight 시작 전에 이미 알고 있었으면서도 문서화만 하고 실제 실행 때 빼먹을 뻔**. 다행히 발견하고 `caffeinate -di nohup` 으로 launch.
- **실 비용 tracking이 Sprint 4에야 붙음**: Sprint 0~3 도중 "지금 비용 얼마 썼나"를 실시간으로 알 방법이 Sprint 4의 `cost_ledger.jsonl` 생기기 전까진 없었음. 초기부터 공용 cost_tracker 모듈 두는 게 맞았음.

---

## 교훈 → 차기 챌린지 규칙화

1. **환경 변경 전파 강제 (신규 CLAUDE.md 원칙 #9)**: Sprint 0이 기반 환경(venv, docker v2, 경로 규약, package layout 등)을 변경하면 **같은 세션 안에서** Sprint 1+의 `checkpoint_sprintN.sh`와 `VERIFY.sh`에 동일 변경 propagate. 미루면 cascade fail.
2. **Checkpoint 멱등성 (신규 CLAUDE.md 원칙 #10)**: 모든 `checkpoint_sprintN.sh`는 재실행 safe. DB 테이블은 진입 시 TRUNCATE, 파일 출력은 `rm -rf`, side-effect 테이블(event_cooldown 등)은 사전 clear. 세션 내부와 외부 재실행 환경이 다를 수 있음을 전제.
3. **docker compose v2 표준 (신규 CLAUDE.md 원칙 #11)**: `docker compose` (스페이스) 문법 표준. `docker-compose` (하이픈) 사용 금지. Docker Desktop 최근 버전은 v1 없음.
4. **API 키 없이도 하네스 생존 (신규 CLAUDE.md 원칙 #12)**: `ANTHROPIC_API_KEY` env var hard-check preflight 금지. Claude Code는 keychain 인증 지원. 실제 확인은 `claude -p "ping" --model haiku` 호출로. Replay fixture fallback 패턴 기본 장착.
5. **macOS 슬립 방지 명시 (PLAYBOOK 섹션 신설)**: 사전 체크리스트에 `caffeinate -di nohup bash ...`를 **사용자 실행 명령의 일부**로 박음. 문서에만 있고 launch 순간 빼먹으면 리밋 회복 깨짐.
6. **/loop 10m periodic status 패턴 채택 (PLAYBOOK 추가)**: 오버나이트 중 사용자가 깨어있거나 깨는 즉시 히스토리 확인하고 싶을 때, `CronCreate '*/10 * * * *'` + 상태 스냅샷 프롬프트로 self-pace. 이 RETRO도 그 덕에 중간 이벤트(half_scope) 즉시 감지.
7. **`/office-hours` → `/oh-my-claudecode:ralplan` 사전 적용을 PLAYBOOK §2 기본 절차로**: challenge-1엔 없던 단계. 23개 사전 이슈 잡아냈음. 추후 모든 챌린지에 강제.

**반영 위치** — 이 RETRO 커밋 같은 커밋에 함께:
- `CLAUDE.md` — 원칙 8개 → **12개**로 확장 + 리밋 대응에 caffeinate 추가
- `PLAYBOOK.md` — §2에 office-hours/ralplan 선행 단계, §3에 overnight.sh 템플릿 개선, §4에 기상 후 `.half_scope` 확인 + /loop 모니터링 패턴
- `challenge-2/HARNESS.md` — "실측 결과" 섹션 채움
