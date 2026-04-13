# Challenge-1 Retrospective — Warehouse Picker VLA

**기간**: 2026-03-29 ~ 2026-03-30 (오버나이트 랄프톤)
**주제**: 로봇 픽킹 에이전트 (Planner + Verifier + Task Manager + VLA 모델)
**결과**: Sprint 0~5 완료, 최종 Demo + Polish까지 커밋

---

## 진행 타임라인

사전 문서(2~3시간) → 오버나이트 실행(자는 동안) → 기상 후 검증.

| 세션 | 커밋 | 내용 |
|------|------|------|
| Sprint 0 | `5410fcc` | Risk validation |
| Sprint 1 | — | Simulation env |
| Sprint 2 | `5410fcc` | VLA integration |
| Sprint 3 | `d4ac62c` | Agentic orchestrator |
| Sprint 4 | `07b2d3c` | Error recovery + multi-item |
| Sprint 5 | `3b88bab` | Expansions + demo + polish |
| Docs | `6141e71` | Known limitations, execution plan |

실행 방식: `scripts/overnight.sh`가 `claude -p --dangerously-skip-permissions` 세 번 호출, 사이에 `sleep 900`로 레이트 리밋 회피.

---

## 잘된 점 (재사용할 패턴)

- **사전 문서 선행**: `docs/EXECUTION_PLAN.md`, `PRD.md`, `TECH_STACK.md`를 먼저 완성해놓고 시작 → Claude가 무엇을 해야 할지 방황 안 함
- **TDD 강제**: "write test files FIRST" 프롬프트 규칙 덕분에 기상 후 `pytest`만 돌려도 검증 가능
- **Sprint별 progress 리포트**: `docs/progress/sprint-N.md`에 뭘 했는지/이슈/해결/테스트 결과 기록 → 회고 자료가 자동 생성됨
- **Docker + 로컬 분리**: Gazebo는 Docker, SmolVLA는 MPS — 아침에 각각 독립 검증 가능
- **커밋 단위 분리**: 스프린트 하나 = 커밋 하나, 롤백 쉬움

## 문제점

- **리밋에 걸려서 중간에 끊김** (가장 큰 문제): `sleep 900`은 경험적 값이라 진짜 5시간 윈도우 회복을 보장 못 함. 끊기면 내 개입 전까지 대기
- **프롬프트 로그 흩어짐**: `overnight_session1/2/3.log`만 있고 "내가 뭘 지시했는지" 통합 로그가 없어 회고 때 수작업 재구성 필요
- **하드코딩된 절대 경로**: `cd /Users/leesanghun/My_Project/VLA` — 레포 이름 바뀌니 스크립트가 깨짐
- **수동 검증 가이드 부재**: 기상 후 "결과를 어떻게 돌려봐야 하는지"가 docs 여기저기 흩어져 있음. 웹 프로젝트면 URL 하나면 되지만 로보틱스는 재현 절차 명시 필요

## 아쉬운 점

- 주제가 랄프톤에 **무거웠음**: 시뮬레이션(Docker+Gazebo) + ML 모델 로딩이 엮여서 한 번 깨지면 복구가 오래 걸림. 다음엔 외부 의존 적은 주제
- 자동 재개(auto-resume) 로직이 없어서 세 세션 모두 "성공했다고 가정"하고 진행

## 교훈 → 차기 챌린지 규칙화

1. **랄프톤 적합 주제**: 외부 서비스/GPU/시뮬레이터 의존 최소화. 순수 코드 + 단위 테스트 위주.
2. **타임라인 + 프롬프트 로그 필수화**: `challenge-N/TIMELINE.md` + `challenge-N/prompts/*.txt` 강제
3. **리밋 회복 자동화**: 단순 sleep 말고 **성공 감지 → 다음 세션 / 실패 감지 → 리밋 해제까지 대기 → 재시도** 루프
4. **기상 후 검증 1-command**: `make verify` 또는 `bash challenge-N/VERIFY.sh` 하나로 결과 재현

이 네 가지를 루트 `CLAUDE.md` + `PLAYBOOK.md`에 박아서 차기 챌린지부터 자동 적용.
