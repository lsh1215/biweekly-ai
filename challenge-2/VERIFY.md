# challenge-2 VERIFY

기상한 사용자가 **첫 5분 안에** 재현할 수 있도록 설계. 이 파일은 설명, `VERIFY.sh`는 실행.

## 전제

- **macOS 사용자는 overnight 실행 시 `caffeinate -di nohup bash scripts/overnight.sh &` 필수** — 노트북이 슬립으로 들어가면 `sleep 5h10m` 리밋 백오프 카운터가 멈춰 회복이 깨진다. Linux는 `systemd-inhibit --what=sleep nohup bash scripts/overnight.sh &`.
- VERIFY.sh 실행 단계에는 `ANTHROPIC_API_KEY`가 필요 없다 — replay fixture로 결정론적으로 동작. 라이브 재녹화를 하려면 키를 설정하고 `python -m ria.cli healthcheck --record tests/fixtures/replay/healthcheck.json ...`을 실행.

## 한 줄 명령

```bash
cd challenge-2 && bash VERIFY.sh
```

## 사전 설정 (Sprint 0에서 이미 준비됨)

1. Python 3.11+
2. Docker Desktop 또는 Docker Engine 실행 중
3. `.venv` 활성화는 `VERIFY.sh` / checkpoint 스크립트가 자동 처리 (homebrew PEP 668)
4. `git status`가 challenge-2 브랜치에서 클린
5. `.half_scope` 파일 없음 (있으면 이전 실행 잔재 — 검토 후 삭제)

## VERIFY.sh가 하는 일

```
1. 기존 컨테이너 정리 → docker-compose up -d postgres
2. Postgres 준비 대기 (pg_isready)
3. pip install -e . (editable)
4. 전체 pytest 회귀 (Sprint 0~4 통합)
5. fixture 로드 확인
6. ria healthcheck 실행 (planned report 1개 생성)
7. ria process-events --queue tests/fixtures/synthetic_events/ 실행
   → P0 1건 interrupt 리포트 생성, P2 1건 무시, 중복 1건 쿨다운
8. 생성 리포트 파싱:
   - 파일 존재 확인 (planned_*.md + interrupt_P0_*.md)
   - 첫 200자에 action verb 존재 (BUY|HOLD|REDUCE|WATCH|REVIEW)
   - 본문에 citation ≥ 3개 (https:// 또는 accession)
9. pgvector 공시 청크 ≥ 10 SQL 확인
10. cost_summary.md 파싱 (strict regex: 첫 줄이 `total $X.XX` 리터럴) → 총 비용 ≤ $50 확인. 첫 줄 포맷 다르면 fail.
11. 모든 체크 통과 시 "CHALLENGE-2 VERIFIED ✓" 출력, exit 0
```

## 예상 출력 (성공 시)

```
[1/10] Cleaning up...                         OK
[2/10] Starting Postgres...                   OK
[3/10] Installing package...                  OK
[4/10] Running pytest...                      42 passed
[5/10] Loading fixtures...                    prices=10, news=10, filings=5
[6/10] Running weekly healthcheck...          reports/planned_20260418.md (1842 bytes)
[7/10] Processing events...                   reports/interrupt_P0_tsla.md (1203 bytes)
[8/10] Validating reports...                  action_verb=OK, citations=5
[9/10] Checking pgvector corpus...            chunks=14 (≥ 10 OK)
[10/10] Cost summary...                       $12.40 / $50.00 budget OK

CHALLENGE-2 VERIFIED ✓
```

## 실패 시 진단

- Postgres 기동 실패 → `docker-compose logs postgres` 확인
- pytest 실패 → 실패한 테스트명으로 `TIMELINE.md`에서 관련 스프린트 로그 조회
- 리포트 파일 없음 → `logs/` 내 해당 세션 로그 + `ria healthcheck --verbose` 재실행
- Citation 부족 → Sprint 2/3에서 RAG 활용 실패. `rag_search` tool 호출 로그 확인
- pgvector chunk 부족 → Sprint 1 ingest 미완. `python -m src.ria.ingest.filings --reingest` 재실행
- Cost 초과 → `reports/cost_summary.md` 세부 항목 확인, Haiku-downshift 미적용 가능성

## 재현 데모 (30초)

`VERIFY.sh`의 7~8단계 리포트 2개만 확인하면 "밤사이 뭐 했나" 즉각 파악 가능:

```bash
cat reports/planned_*.md | head -40
cat reports/interrupt_P0_*.md | head -40
```
