# biweekly-ai

2주에 하나씩 AI로 뭔가 만드는 개인 레포.

각 챌린지는 `challenge-N/` 디렉토리 안에 독립적으로 들어간다.

## Challenges

| # | 제목 | 설명 | 상태 |
|---|------|------|------|
| [challenge-1](./challenge-1) | Warehouse Picker VLA | 로봇 픽킹 에이전트 — Planner/Verifier/Task Manager + SmolVLA 통합 (Claude LLM + Vision) | 완료 · 140 tests pass |
| [challenge-2](./challenge-2) | Reactive Investment Agent (RIA) | 서학개미용 포트폴리오 관리 CLI — Opus 4.7 판단 + Haiku 4.5 severity + pgvector 공시 RAG + 이벤트 interrupt | 완료 · 116 tests pass · VERIFY 10/10 · $0.50 / $50 |
| [challenge-3](./challenge-3) | aiwriting Claude Code Plugin | 한국어 멀티포맷 글쓰기 플러그인 — writer/scrubber/copy-killer/structure-critic/fact-checker × blog/cover-letter/paper/letter | 완료 · 113 tests pass · VERIFY 10/10 · dogfood 4/4 · ~$5.3 / $7.5 |

## 규칙

- 2주 한 사이클, 한 디렉토리에 모든 것(코드, 문서, 노트) 자급자족
- 디렉토리 이름은 `challenge-{n}` 순차 증가
- 각 `challenge-N/`는 자체 README·의존성·테스트를 가진다
- 작업 방식은 **오버나이트 랄프톤** (자기 전 문서 → 자는 동안 자율 실행 → 기상 후 검증)

## 운영 문서

- [`CLAUDE.md`](./CLAUDE.md) — Claude가 지킬 규칙 (자동 로드, 12개 불변 원칙)
- [`PLAYBOOK.md`](./PLAYBOOK.md) — 오버나이트 프로토콜 상세
- [`HARNESS.md`](./HARNESS.md) — 하네스 엔지니어링 원칙 + 도구 카탈로그
- [`challenge-1/RETRO.md`](./challenge-1/RETRO.md) — 1차 회고 (VLA 로봇 픽킹)
- [`challenge-2/RETRO.md`](./challenge-2/RETRO.md) — 2차 회고 (RIA, 4개 신규 원칙 도출 → CLAUDE.md §9~12 반영)
- [`challenge-3/TIMELINE.md`](./challenge-3/TIMELINE.md) — 3차 overnight audit trail (Planner/Architect/Critic 합의 → Sprint 0~3 자율 실행 + 자가 결정 3건)
