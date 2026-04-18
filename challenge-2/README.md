# RIA — Reactive Investment Agent (challenge-2)

한국 거주 서학개미 중급자의 **잠자는 미국주식 3~5종목 포트폴리오**를
주간 헬스체크 + 이벤트 트리거 off-cycle 리포트로 자율 관리하는 단일
에이전트 CLI. Claude Opus 4.7 (판단) + Haiku 4.5 (이벤트 severity
분류) + pgvector (공시 RAG) 기반.

## 빠른 시작

```bash
# 1) Postgres + pgvector 컨테이너 기동
docker compose up -d postgres

# 2) 패키지 설치 (editable)
pip install -e .

# 3) 주간 헬스체크 (replay 모드 — ANTHROPIC_API_KEY 불필요)
python -m ria.cli healthcheck \
  --portfolio portfolio.example.yaml \
  --replay tests/fixtures/replay/healthcheck.json \
  --out reports/

# 4) 이벤트 큐 처리 (P0 → interrupt 리포트, P1/P2 → 저널 deferred)
python -m ria.cli process-events \
  --queue tests/fixtures/synthetic_events/ \
  --portfolio portfolio.example.yaml \
  --out reports/
```

전체 E2E 검증은 `bash VERIFY.sh` 하나로 끝난다 — VERIFY.md 참조.

## 디렉토리 가이드

- `src/ria/` — CLI, 에이전트 루프, 툴 (prices/news/rag/emit_report),
  severity classifier, decision journal, cost tracker
- `tests/` — Sprint 0~4 pytest (fixture-first, DB 필요 테스트는
  `RIA_SKIP_DB_TESTS=1`로 스킵 가능)
- `data/fixtures/` — 가격/뉴스/10-K 60일치 커밋된 fixture
- `reports/` — 런타임 산출물 (planned / interrupt markdown + cost_summary.md)
- `scripts/overnight.sh` — 외부 쉘 루프 (리밋 감지 → 5h10m 백오프 → 재시도)
- `prompts/session-*.txt` — 각 스프린트 오버나이트 세션 프롬프트

## 비용

Claude API 총 사용 상한 **$50**. 실행마다 `reports/cost_summary.md` 첫 줄
`total $X.XX`로 기록되며, VERIFY.sh가 exit 1로 초과를 가드한다.

## 더 읽을거리

- `PRD.md` — 문제/타깃/성공 기준/Non-goals
- `EXECUTION_PLAN.md` — 스프린트 분할 + checkpoint 스크립트 규약
- `TECH_STACK.md` — 라이브러리·모델·pgvector 선택 근거
- `HARNESS.md` — 도구·훅·스킬 선택 기록
- `TIMELINE.md` — 오버나이트 실행 로그 (무인 결정 audit trail)
