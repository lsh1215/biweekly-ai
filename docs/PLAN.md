# Warehouse Picker — 실행 플랜

> 이 문서를 새 세션에서 열고 순서대로 진행하세요.
> 최종 업데이트: 2026-03-29

---

## 현재 상태

### 완료된 작업

- [x] 프로젝트 초기 설정 (.gitignore, .claude/)
- [x] OMC 플러그인 설치 및 설정 (v4.9.3)
- [x] anthropics/skills 마켓플레이스 추가
- [x] gstack 설치 및 setup 완료
- [x] VLA/에이전틱 시스템 리서치 완료
- [x] 시뮬레이터 비교 리서치 완료 (Gazebo 선택)
- [x] 구독 기반 실행 방법 리서치 완료 (`claude -p`)
- [x] 기술 스택 문서 작성 (`docs/TECH_STACK.md`)
- [x] PRD 문서 작성 (`docs/PRD.md`)
- [x] 주제 확정: **Warehouse Picker (물류 창고 피킹 로봇)**

### 미완료 작업 (여기서부터 이어서)

- [x] gstack CEO 리뷰 → PRD 스코프 검증 (SELECTIVE EXPANSION, 4개 확장 채택)
- [ ] gstack Eng 리뷰 → 기술 스택 타당성 검증
- [ ] 환경 구축 시작

---

## 다음 단계 (순서대로)

### Step 1: PRD 스코프 검증 (gstack)

```
/plan-ceo-review
```

실행 후 `docs/PRD.md`를 읽도록 안내하세요:
> "docs/PRD.md를 읽고 Warehouse Picker 프로젝트의 스코프를 CEO 관점에서 리뷰해줘"

**검증 포인트:**
- MVP 스코프가 포트폴리오로 충분히 인상적인가?
- Phase 2/3이 현실적인가?
- 5주 마일스톤이 적절한가?

### Step 2: 기술 스택 검증 (gstack)

```
/plan-eng-review
```

실행 후:
> "docs/TECH_STACK.md와 docs/PRD.md를 읽고 기술 아키텍처를 Eng 관점에서 리뷰해줘"

**검증 포인트:**
- SmolVLA + Gazebo + `claude -p` 조합이 실제로 동작하는가?
- 상태 머신 설계에 빠진 엣지 케이스는?
- ROS2 노드 분리가 적절한가?
- M2 Pro 32GB에서 Docker + Gazebo + SmolVLA 동시 실행이 가능한가?

### Step 3: 리뷰 결과 반영

CEO/Eng 리뷰 피드백을 PRD와 TECH_STACK에 반영:
> "리뷰 결과를 docs/PRD.md와 docs/TECH_STACK.md에 반영해줘"

### Step 4: 환경 구축 (M1 마일스톤)

```bash
# Docker + ROS2 + Gazebo 세팅
# PRD의 마일스톤 M1 참고
```

> "docs/PRD.md의 마일스톤 M1을 실행해줘. Docker + ROS2 + Gazebo 환경을 세팅하고 창고 월드를 만들어줘"

### Step 5: VLA 통합 (M2 마일스톤)

> "SmolVLA 모델을 로딩하고 MPS에서 추론 테스트해줘. 그다음 ROS2 Executor 노드를 만들어줘"

### Step 6: 오케스트레이터 구현 (M3 마일스톤)

> "claude -p를 래핑한 Planner와 Verifier를 구현하고, Task Manager 상태 머신을 만들어줘"

### Step 7: 오류 복구 + 통합 (M4 마일스톤)

> "그립 실패 감지, 물체 낙하 재피킹, 멀티 아이템 순차 처리를 구현해줘"

### Step 8: 데모 + 문서화 (M5 마일스톤)

```
/ship
/document-release
```

---

## 핵심 파일 위치

| 파일 | 설명 |
|---|---|
| `docs/PRD.md` | 제품 요구사항 (기능, 아키텍처, 마일스톤) |
| `docs/TECH_STACK.md` | 기술 스택 + 참고 논문/레퍼런스 |
| `docs/PLAN.md` | 이 문서 (실행 플랜) |

## 기술 스택 요약

| 레이어 | 기술 |
|---|---|
| Planner/Verifier | `claude -p` (Max 구독, API 키 불필요) |
| Executor | SmolVLA (450M) + PyTorch MPS |
| Middleware | ROS2 Jazzy |
| Simulator | Gazebo Harmonic (Docker) |
| Hardware | MacBook Pro M2 Pro 32GB |

## gstack 스킬 활용 가이드

| 단계 | 스킬 | 용도 |
|---|---|---|
| 기획 | `/plan-ceo-review` | PRD 스코프 챌린지 |
| 기획 | `/plan-eng-review` | 아키텍처 검증 |
| 기획 | `/autoplan` | CEO+Eng+Design 한방 리뷰 |
| 개발 | `/freeze src/vla/` | VLA 코드 잠그고 에이전트만 수정 |
| 개발 | `/investigate` | 시뮬레이션 버그 근본 원인 분석 |
| 리뷰 | `/review` | 코드 리뷰 |
| 보안 | `/cso` | API 키 관리, Docker 보안 감사 |
| 배포 | `/ship` | PR 생성 |
| 문서 | `/document-release` | 배포 후 문서 동기화 |
