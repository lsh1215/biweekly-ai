# challenge-2 PRD — Reactive Investment Agent (RIA)

**Status**: APPROVED 2026-04-18 (design doc: `~/.gstack/projects/lsh1215-biweekly-ai/leesanghun-main-design-20260418-054439.md`)
**Range**: Sprint 0~4 (5 sprints, overnight-executable)
**Budget**: Claude API ≤ $50 total

## 1. 한 줄 설명

한국 거주 서학개미 중급자의 잠자는 미국주식 3~5종목 포트폴리오를 **주간 헬스체크 + 이벤트 트리거 off-cycle 리포트**로 자율 관리하는 단일 에이전트 CLI.

## 2. 왜 (Problem)

타깃 세그먼트는 미국 주식을 보유하지만 **시차·영어 장벽·규율 부재** 3중 벽 때문에 "산 뒤 방치" 상태에 고착됨. 기존 한국 증권사 AI는 (a) broker-locked, (b) 자사 상품 bias, (c) 챗봇+요약 수준 — 이 공백이 wedge.

**본인 dogfood = primary validation**. 외부 인터뷰 = overnight 무인 실행과 충돌하므로 post-challenge 선택사항.

## 3. 타깃 사용자

한국 거주, 미국 개별주 long-only 3~5종목, 중기 보유 지향, 영어 직접 소화 부담, 평일 장중 대응 시간 없음.

**v1 제외**: ETF · 옵션 · 단주 · 공매도 · 멀티 증권사 통합 import · 실거래.

## 4. 핵심 가치 (Wedge)

1. **주간 헬스체크** — 매주 월 06:00 KST 기준 포트폴리오 리포트 1개
2. **이벤트 off-cycle 리포트** — 보유 종목 직접 hit (severity = **P0**) 이벤트 발생 시 즉시 추가 리포트. **v1 범위에서 P1(섹터 macro)은 interrupt 대신 next planned cycle에 집계**, P2는 무시.
3. **영문 원문 → 한국어 + 내 포지션 맥락 해석** — 증권사 번역 지연 + 일반 AI 대비 우위
4. **Agentic RAG** — 에이전트가 pgvector 코퍼스 검색 필요성·깊이를 스스로 결정

## 5. 성공 기준 (VERIFY.sh hard gates)

모두 통과해야 챌린지-2 완료:
1. `VERIFY.sh` E2E 실행 성공 (exit 0)
2. Planned 리포트 1개 + Interrupt 리포트 1개 파일 생성
3. 두 리포트 첫 200자 안에 action verb(`BUY`|`HOLD`|`REDUCE`|`WATCH`|`REVIEW`) 최소 1개
4. 의사결정 근거 링크(뉴스 URL 또는 SEC accession ID) — planned 리포트 **≥ 2개**, interrupt 리포트 **≥ 1개**, 전체 합산 **≥ 3개**
5. pgvector 공시 청크 ≥ 10 (ingest 확인)
6. Sprint 0~4 pytest 전체 통과
7. Claude API 총 비용 ≤ $50

**Soft gates** (실패 시 `TIMELINE.md` 경고만):
- 포트폴리오 YAML hot-reload (Sprint 4에서 가능하면)

## 6. Non-goals (명시적 제외)

- 실제 브로커 연동 및 주문 집행
- 웹 UI, 모바일 앱, 푸시 알림
- 실시간 cron 데몬 (VERIFY.sh 내 1회 사이클 시뮬레이션만)
- PDF 리포트 (markdown only)
- 멀티에이전트 committee (차기 챌린지 RFC)
- Broker-agnostic 통합 import (차기 챌린지 RFC)
- KRW 환산 (v0.2)
- **P1 severity interrupt** (v1은 P0만 즉시 interrupt, P1/P2는 next planned cycle로 집계/deferred)

## 7. 차기 챌린지 후보 (여기선 구현 X)

- 멀티에이전트 분할 (planner/executor/reviewer)
- 실시간 cron 데몬 + 이메일/Slack 통합
- 다수 증권사 CSV/XLS import
- 실거래 broker 연결 (KIS Developers API 등)

## 8. 제약 (잠금)

- **언어/런타임**: Python 3.11+
- **LLM**: Claude Opus 4.7 (판단) + Haiku 4.5 (severity classify)
- **Vector DB**: PostgreSQL 16 + pgvector 0.7+ (docker-compose)
- **Embedding**: `sentence-transformers/all-MiniLM-L6-v2` (로컬, 무료)
- **Fixture-first**: 모든 외부 데이터 사전 다운로드 후 커밋, 런타임 네트워크 독립
- **TDD 강제**: `src/ria/**` strict, `scripts/*.py`는 smoke test 1개로 갈음
- **무인 실행**: 질문 금지, 모호하면 `TIMELINE.md` 기록 후 진행
- **경로 규약**: 모든 상대경로는 **`challenge-2/` 루트 기준**. `docker-compose.yml`, `pyproject.toml`, `data/fixtures/`, `reports/`, `tests/` 전부 `challenge-2/` 하위.
- **Package layout**: `src/` layout (`[tool.setuptools.packages.find] where=["src"]`). 모든 import = `from ria.xxx` (접두 `src.` 금지).
- **비용 상한**: Claude API 총 사용 ≤ **$50**. 초과 감지 시 `VERIFY.sh` fail.

## 9. 참조

- Design doc: `~/.gstack/projects/lsh1215-biweekly-ai/leesanghun-main-design-20260418-054439.md`
- 레포 규칙: `../CLAUDE.md`
- 하네스 원칙: `../HARNESS.md`
- 오버나이트 프로토콜: `../PLAYBOOK.md`
