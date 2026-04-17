# challenge-2 TECH STACK

각 선택에 왜(why)를 한 줄씩. 변경 시 PRD §8 "제약 잠금"도 동기화.

## Runtime & Language

| 항목 | 선택 | 왜 |
|-----|-----|---|
| Language | Python 3.11+ | 금융 데이터 툴링(pandas, yfinance) + Anthropic SDK 표준 |
| Package mgmt | `pyproject.toml` + `uv` (설치 빠름) | `pip install -e .` 가능 |
| Type hints | mypy strict on `src/` | TDD와 궁합, tool schema 정확성 |

## LLM

| 항목 | 선택 | 왜 |
|-----|-----|---|
| Primary | Claude Opus 4.7 | 판단·리포트 생성. tool use 신뢰도·한국어 품질 |
| Classifier | Claude Haiku 4.5 | severity 분류 빠름·저렴. Opus가 호출하는 tool wrapper로 격리 |
| Embedding | `sentence-transformers/all-MiniLM-L6-v2` | 로컬 CPU 가능, 무료, 384차원 pgvector 궁합. Voyage는 cost 이유로 v1 제외 |
| SDK | `anthropic` (공식 Python SDK) | messages API + tool_use 표준 |

## Data / Storage

| 항목 | 선택 | 왜 |
|-----|-----|---|
| Vector DB | **PostgreSQL 16 + pgvector 0.7+** | 사용자 요구사항. HNSW 인덱스, SQL 통합 조회 가능 |
| Journal | 동일 Postgres | 분리 비용 없이 audit trail |
| Fixture storage | 일반 파일시스템 (`data/fixtures/`) | 버전 컨트롤 친화, 네트워크 독립 |
| Local cache | 없음 (fixture가 이미 캐시 역할) | YAGNI |
| DB 구동 | Docker Compose 단일 파일 | 1-command boot |

## 외부 데이터 (Fixture-first)

| 데이터 | 소스 | 수집 방식 | 런타임 접근 |
|-------|-----|--------|-----------|
| 일봉 OHLCV | `yfinance` | Sprint 0 `fetch_fixtures.py` 1회 | `data/fixtures/prices/*.csv` |
| 뉴스 | Yahoo Finance news RSS | 동일 | `data/fixtures/news/*.json` |
| 공시 | SEC EDGAR (User-Agent 필수) | 수동 선별 + 스크립트 | `data/fixtures/filings/*.txt` |
| 이벤트 | 수작업 합성 | 직접 작성 | `tests/fixtures/synthetic_events/*.json` |
| Market calendar | `pandas_market_calendars` NYSE | 런타임 로컬 라이브러리 | (네트워크 불요) |

**선언**: 챌린지-2 중 런타임에 외부 네트워크 호출은 Anthropic API 한 곳뿐이다.

## Application

| 항목 | 선택 | 왜 |
|-----|-----|---|
| CLI | `typer` | 타입 기반 명령 정의, Click보다 간결 |
| Config | `portfolio.yaml` + Pydantic | schema validation |
| Report format | Markdown | 읽기 쉬움·grep 가능·LLM 생성 친화. PDF는 v0.2 |
| Async | 필요 최소 (이벤트 큐 drain 정도) | 복잡도 회피 |
| Logging | 표준 `logging` → stderr + `logs/` 파일 | 토큰/비용 기록 포함 |

## Testing

| 항목 | 선택 | 왜 |
|-----|-----|---|
| Framework | `pytest` + `pytest-asyncio` | 표준 |
| LLM in tests | `VCR.py` 또는 replay fixture | 결정론 확보 |
| Cost in CI | cost probe 1회 측정 값 | budget 잠금 |

## Dev tooling

| 항목 | 선택 | 왜 |
|-----|-----|---|
| Formatter | `ruff format` | black + isort 통합 |
| Lint | `ruff check` | 빠름 |
| Pre-commit | skip (overnight 속도 우선) | TDD + pytest가 실질 게이트 |

## 외부 서비스 계정

| 서비스 | 필요? | 비고 |
|-------|-----|-----|
| Anthropic | **O** | 사용자 API 키 (총 비용 ≤ $50) |
| Yahoo Finance | X | yfinance 라이브러리(비공식) 사용, 계정 불필요 |
| SEC EDGAR | X | User-Agent 헤더만 필수 |
| Postgres | X | 로컬 Docker |
| GDELT | X (v1 제외) | noise 높아 1차 소스 아님 |
| Voyage AI | X (v1 제외) | 비용 이유로 로컬 임베딩 채택 |

## 버전 잠금 (Sprint 0이 확정)

**프로세스**:
1. Sprint 0 세션이 시작할 때 `pip index versions <pkg>`로 **현재 pypi 최신 stable** 확인.
2. 각 주요 deps를 그 값 기준 `~=major.minor`로 `pyproject.toml`에 고정.
3. 같은 세션에서 이 `TECH_STACK.md` 표도 실측 값으로 **동시 갱신**.
4. 이후 Sprint 1~4는 Sprint 0이 잠근 버전 그대로 사용. 변경 금지.

**해당 시점까지 baseline 참고값** (Sprint 0이 최신 stable로 덮어씀):

| 패키지 | baseline | 비고 |
|-------|---------|-----|
| anthropic | TBD (Sprint 0) | messages API tool_use 표준 |
| sentence-transformers | TBD | MiniLM-L6-v2 384-dim |
| pgvector | TBD | HNSW 인덱스 |
| psycopg[binary] | TBD | Postgres 드라이버 |
| pandas | TBD | |
| pandas_market_calendars | TBD | NYSE calendar |
| typer | TBD | CLI |
| pytest + pytest-vcr | TBD | VCR 녹화/재생 |

## 경로 규약

- **모든 상대경로는 `challenge-2/` 루트 기준**. docker-compose, pyproject, data/, reports/, tests/, src/ 전부 `challenge-2/` 하위.
- VERIFY.sh는 `cd challenge-2` 상태에서 실행되도록 설계됨 (스크립트가 자동으로 자기 디렉토리로 이동).

## Package layout

- `src/` layout. `[tool.setuptools.packages.find] where=["src"]`.
- 모든 import: `from ria.xxx import ...`. 접두 `src.` 금지.
- 실행: `python -m ria.cli <cmd>` 또는 console script `ria <cmd>` (pyproject 진입점).
