# challenge-2 EXECUTION PLAN

**원칙**: 스프린트 끝 = 테스트 통과 = 커밋. 각 스프린트는 자급자족, 다음 스프린트로 넘어갈 때 checkpoint 스크립트로 green 확인.

**경로 규약**: 모든 상대경로는 `challenge-2/` 루트 기준.

---

## Sprint 0 — 스켈레톤 + Fixture + Cost probe

**목표**: 챌린지 전체의 인프라 확정. 런타임 네트워크 독립 확보.

**산출물**:
- `pyproject.toml` (src layout, Sprint 0 시점 pypi 최신 stable 버전으로 anthropic resolve. deps: anthropic, typer, sentence-transformers, psycopg, pgvector, pandas, pandas_market_calendars, pyyaml, pydantic≥2, pytest, pytest-vcr, yfinance)
- `docker-compose.yml` (image: `pgvector/pgvector:pg16`, DB/user/password: `ria`)
- `src/ria/models.py` — Portfolio / Position Pydantic v2
- `portfolio.example.yaml` — 3종목 AAPL/TSLA/NVDA, TSLA 55% 집중
- `scripts/fetch_fixtures.py` — 1회 다운로드 스크립트:
  - **가격** (yfinance): 10 tickers × **과거 60일** → `data/fixtures/prices/{TICKER}.csv`
  - **뉴스** (Yahoo Finance news RSS): 티커별 최근 30개 → `data/fixtures/news/{TICKER}.json`
  - **공시** (SEC EDGAR full-text search API): 티커당 최근 10-K 1개 + 선택적 10-Q, 최소 5개 성공 → `data/fixtures/filings/{TICKER}_{FORM}_{DATE}.txt`. User-Agent 고정. Per-accession 3회 exp backoff.
  - **Fallback**: 5개 미달 시 stub 파일로 채움 (TIMELINE에 `FIXTURE_FALLBACK=sec_edgar_partial` 기록).
- `scripts/cost_probe.py` — Claude API 1회 호출 (Haiku tiny prompt) + 오버나이트 예상 비용 추정. 마지막 줄: `estimated_total_usd=X.XX` 리터럴.
- `tests/test_fixtures.py`, `tests/test_portfolio_schema.py`

**Checkpoint** (`scripts/checkpoint_sprint0.sh`):
```bash
pytest tests/test_fixtures.py tests/test_portfolio_schema.py -q
docker-compose up -d && pg_isready 체크
python scripts/cost_probe.py > logs/cost_probe.txt
grep -qE '^estimated_total_usd=' logs/cost_probe.txt
test -f data/fixtures/prices/AAPL.csv
test -f data/fixtures/news/AAPL.json
[ $(find data/fixtures/filings -name '*.txt' | wc -l) -ge 5 ]
```

**커밋**: `feat(challenge-2): sprint 0 — scaffold + fixtures + cost probe`

---

## Sprint 1 — Tool primitives + RAG ingest

**목표**: 에이전트가 호출할 Python 도구들 구현 + 공시 pgvector 코퍼스 빌드.

**산출물**:
- `src/ria/tools/prices.py` → `get_prices(tickers, window_days) -> DataFrame` (비거래일 처리, NYSE calendar)
- `src/ria/tools/news.py` → `get_news(ticker, last_n_days) -> list[Article]`
- `src/ria/tools/rag.py` → `rag_search(query, top_k) -> list[Chunk]` (pgvector HNSW)
- `src/ria/ingest/filings.py` — 공시 → MiniLM-L6-v2 (384-dim) → pgvector (HNSW 디폴트 params)
- `src/ria/db/schema.sql` — `filings_chunks` 테이블 + pgvector extension 활성화
- `tests/test_tools_prices.py`, `test_tools_news.py`, `test_tools_rag.py` — 엣지 케이스 (빈 fixture, 누락 티커, 주말/휴장일, fixture 범위 밖)

**TDD**: `src/ria/**` strict. 각 tool 함수 테스트 먼저.

**Checkpoint** (`scripts/checkpoint_sprint1.sh`):
```bash
pytest tests/test_tools_*.py -q
python -c "from ria.tools.rag import rag_search; ..."   # import는 'ria.xxx', 접두 'src.' 금지
docker-compose exec postgres psql ... "SELECT COUNT(*) FROM filings_chunks;"  # ≥ 10
```

**커밋**: `feat(challenge-2): sprint 1 — price/news/rag tools + filings ingest`

---

## Sprint 2 — Agent loop + Weekly healthcheck (replay mode 필수)

**목표**: Claude SDK tool-use 루프 + planned 주간 리포트 E2E. `--replay` 플래그로 결정론 확보.

**산출물**:
- `src/ria/agent/loop.py` — Opus 4.7 tool-use 루프, `max_iterations=15`. **`--replay <path>` 지원**.
- `src/ria/agent/prompts/planner.md` — 한국어 리포트, citation ≥ 2, action verb 첫 200자, RAG 쿼리는 영어.
- `src/ria/tools/emit_report.py` → `emit_report(title, sections, citations)`. **citations < 2면 ValueError 발생 (구조적 강제)**.
- `src/ria/cli.py` → `ria healthcheck --portfolio <yaml> [--as-of <date>] [--replay <path>] --out <dir>`. `--as-of` 기본값 = fixture 최대 날짜.
- `tests/test_agent_loop.py` — **3단계 TDD**: (1) unit mock (테스트 먼저) → (2) 라이브 녹화 1회 → `tests/fixtures/replay/healthcheck.json` → (3) replay integration.
- `tests/test_emit_report.py`

**Checkpoint** (`scripts/checkpoint_sprint2.sh`):
```bash
pytest tests/test_agent_loop.py tests/test_emit_report.py -q
python -m ria.cli healthcheck --portfolio portfolio.example.yaml \
  --replay tests/fixtures/replay/healthcheck.json --out reports/
head -c 200 reports/planned_*.md | grep -iE "BUY|HOLD|REDUCE|WATCH|REVIEW"
[ $(grep -cE 'https?://|accession' reports/planned_*.md) -ge 2 ]
```

**커밋**: `feat(challenge-2): sprint 2 — agent loop + replay mode + healthcheck`

---

## Sprint 3 — Severity classifier + Event off-cycle (P0-only v1)

**목표**: Haiku 기반 severity 분류 + **P0만** interrupt 발동. P1/P2는 저널 deferred.

**산출물**:
- `src/ria/tools/classify.py` → Haiku 4.5 호출. input_token 상한 1500.
- `src/ria/agent/event_loop.py`:
  - Severity gate: **P0만** interrupt 리포트 생성. P1/P2는 `decisions` 저널에 `deferred_P1` / `deferred_P2` 기록.
  - 중복 억제: `event_cooldown` 테이블, 동일 event_id 24h 쿨다운. Clock DI (`now_fn`).
- `src/ria/agent/prompts/interrupt.md` — 간결 action-first, citation ≥ 1.
- `src/ria/cli.py` → `ria process-events --queue <dir> --portfolio <yaml> --out <dir>`
- `tests/fixtures/synthetic_events/*.json` — 3개:
  - `evt_tsla_earnings_miss.json` (P0 예상 → interrupt 발동)
  - `evt_random_fintwit_noise.json` (P2 예상 → interrupt 억제 + deferred 저널)
  - `evt_tsla_earnings_miss_DUP.json` (**동일 event_id** 재주입 → 쿨다운 cooldown_skip 저널)
- `tests/test_classify.py` — VCR 녹화
- `tests/test_event_loop.py` — severity gate + cooldown + clock 주입 검증

**Checkpoint** (`scripts/checkpoint_sprint3.sh`):
```bash
pytest tests/test_classify.py tests/test_event_loop.py -q
python -m ria.cli process-events --queue tests/fixtures/synthetic_events/ ...
find reports -name 'interrupt_P0_*.md' | grep -q .   # P0 생성
! find reports -name 'interrupt_P1_*.md' | grep -q . # P1 없음 (v1)
! find reports -name 'interrupt_P2_*.md' | grep -q . # P2 없음
# 저널에 cooldown_skip 1건 이상
```

**커밋**: `feat(challenge-2): sprint 3 — severity classifier + event interrupt (P0-only v1)`

---

## Sprint 4 — Decision journal + Cost summary + 통합

**목표**: `decisions` 저널 테이블 + `cost_summary.md` 생성 + VERIFY.sh 전체 통과.

**산출물**:
- `src/ria/journal.py` — `decisions` 테이블 idempotent CREATE + append API. Sprint 2/3 agent에 hook 추가 (retrofit).
- Cost 측정: 모든 Anthropic API 호출 input/output tokens → `reports/cost_summary.md`.
  **파일 포맷 엄격**:
  ```
  total $12.40
  planned_20260413: input=3214 output=892 usd=0.0421
  interrupt_P0_20260415_TSLA: input=2891 output=720 usd=0.0384
  ...
  ```
  첫 줄 `total $X.XX` 리터럴 (마크다운 헤딩/콜론 금지). $50 초과 시 exit 1. $40 초과 시 TIMELINE `COST_WARN`.
- `VERIFY.md` 보강 (caffeinate 안내).
- `README.md` — soft deliverable (없어도 fail 아님).
- 회귀 테스트 (`pytest` 전체 green — VERIFY.sh 내부에서 실행).

**Checkpoint** (`scripts/checkpoint_sprint4.sh`):
```bash
bash VERIFY.sh   # 포함: pytest + cost 체크 + 10-gate 전체
# pytest 중복 호출 금지 (VERIFY.sh 내부에 이미 있음)
```

**커밋**: `feat(challenge-2): sprint 4 — journal + cost summary + integration`

---

## 오버나이트 매핑 (밤 수 → 스프린트)

| 밤 | Sprint 커버 | 비고 |
|----|-----------|-----|
| 1 | **0 + 1** | 인프라 + tools. RAG ingest는 CPU 임베딩이라 길지만 API 비의존. `.half_scope` 플래그 없으면 Sprint 1 진행. |
| 2 | **2 + (조건부) 3** | Sprint 2 완료 후 `.half_scope` 없으면 Sprint 3 진행. `overnight.sh`가 자동 cascade. |
| 3 | **3 carry-over 혹은 4 + 검증** | 밤 2에서 Sprint 3이 못 들어갔으면 밤 3에 먼저. 아니면 Sprint 4 단독. 기상 후 `bash VERIFY.sh` 1 명령. |

**조건부 체인 (`overnight.sh` 반영)**: 각 sprint 진입 전 `[ -f "$ROOT_DIR/.half_scope" ] && return 0` — 이전 스프린트 half_scope면 downstream 스킵.

Total: **3 밤 (+ buffer)**. 리밋 대응: **최대 2회 재시도** × 5h10m sleep.

---

## 롤백 / 실패 정책

- Sprint N 실패 (2 재시도 소진) → `.half_scope`에 `HALF_SCOPE_FLAG_SPRINT_N` append → 해당 세션 종료.
- `.half_scope` 존재 시 downstream sprint는 **시도하지 않음** (자동 skip, cascade).
- 기상한 사용자가 `.half_scope` 파일과 TIMELINE을 보고 수동 개입 지점 확인.
- Carry-over: 특정 밤에 못 들어간 스프린트는 다음 밤 맨 앞에 실행.
