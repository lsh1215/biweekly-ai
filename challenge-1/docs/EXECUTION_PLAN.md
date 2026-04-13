# Warehouse Picker VLA — Overnight Autonomous Execution Plan

## Context
포트폴리오 프로젝트(Physical AI 취업 타겟)를 7-8시간 동안 자율 실행하여 완성하는 계획. Risk-First 접근법으로 가장 큰 리스크부터 검증 후 M1→M5 순서로 진행. TDD 방법론 적용, 각 스프린트마다 검증 게이트 + 진행 보고서 생성.

## 핵심 결정사항
- **하이브리드 환경**: Gazebo+ROS2는 Docker, SmolVLA는 macOS 로컬(MPS)
- **Docker↔Host 통신**: ZMQ 브릿지 (port 5555/5556) 또는 파일 기반 폴백
- **CEO 확장 4개 포함**: 인터랙티브 방해 데모, 추론 트레이스 UI, A/B 비교 시각화, 구조화된 로깅

---

## 스케줄링 전략 (Rate Limit 대응)

3개 세션으로 분할, 세션 간 15분 쿨다운:

```
00:30  ─── Session 1 ───  Sprint 0 + Sprint 1  (~2.5h)
03:15  ─── Session 2 ───  Sprint 2 + Sprint 3  (~3h)
06:30  ─── Session 3 ───  Sprint 4 + Sprint 5  (~2h)
08:30  ─── DONE ───
```

**실행 스크립트** (`scripts/overnight.sh`):
```bash
#!/bin/bash
cd /Users/leesanghun/My_Project/VLA

echo "=== SESSION 1: Sprint 0+1 ($(date)) ==="
claude -p "Read docs/EXECUTION_PLAN.md. Execute Sprint 0 and Sprint 1. TDD methodology. Write progress to docs/progress/sprint-0.md and sprint-1.md. Follow all acceptance criteria." --max-turns 80

echo "Cooldown 15min..." && sleep 900

echo "=== SESSION 2: Sprint 2+3 ($(date)) ==="
claude -p "Read docs/progress/ for completed sprints. Execute Sprint 2 and Sprint 3 from docs/EXECUTION_PLAN.md. TDD. Write progress reports." --max-turns 80

echo "Cooldown 15min..." && sleep 900

echo "=== SESSION 3: Sprint 4+5 ($(date)) ==="
claude -p "Read docs/progress/ for completed sprints. Execute Sprint 4 and Sprint 5. Final demo + README. Write progress reports." --max-turns 80

echo "=== ALL DONE $(date) ==="
```

---

## Sprint 0: Risk Validation (~45분)

### 목표
가장 큰 리스크 2개 검증: (1) SmolVLA가 MPS에서 로드되는가, (2) `claude -p`가 3D 렌더링 이미지를 판단할 수 있는가.

### 태스크

**0.1 프로젝트 스캐폴딩 (5분)**
```
mkdir -p src/orchestrator/prompts src/executor/models src/simulation/{worlds,models,launch,config} src/common tests configs scripts docs/progress docker
```
생성 파일: `pyproject.toml`, `src/common/types.py`, `src/common/config.py`, `src/common/logger.py`, `configs/warehouse.yaml`, `configs/robot.yaml`, `configs/objects.yaml`

**0.2 Python 의존성 설치 (10분)**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install torch torchvision transformers accelerate pillow pyyaml pytest lerobot pyzmq rich matplotlib
```
검증: `python -c "import torch; print(torch.backends.mps.is_available())"` → `True`

**0.3 SmolVLA MPS 로드 테스트 (10분)**
- TDD: `tests/test_sprint0_smolvla.py` 먼저 작성
  - `test_mps_available()`: MPS 백엔드 확인
  - `test_smolvla_model_loads()`: LeRobot에서 SmolVLA 로드
  - `test_memory_usage()`: 8GB 미만 확인
- 구현: `scripts/validate_smolvla.py`
- **폴백**: SmolVLA 실패 → Octo(90M) → ScriptedPolicy(하드코딩 궤적)

**0.4 claude -p 비전 검증 (10분)**
- TDD: `tests/test_sprint0_vision.py` 먼저 작성
  - `test_claude_p_responds_json()`: JSON 응답 확인
  - `test_claude_p_image_analysis()`: 이미지 판단 정확도
  - `test_claude_p_latency()`: < 10초 확인
- 웹에서 3D 창고 이미지 3-5장 다운로드하여 프록시 테스트
- **Pass 기준**: 5장 중 4장에서 물체 식별 + 위치 판단 정확
- **폴백**: 실패 → Gazebo API(오브젝트 포즈 쿼리)로 프로그래매틱 검증

**0.5 Go/No-Go 결정 + 보고서 (10분)**
- `docs/progress/sprint-0.md` 작성: 모델 선택, 비전 검증 결과, 메모리 프로파일

### 완료 기준
- [x] 프로젝트 스캐폴딩 완성
- [x] Python venv + 의존성 설치
- [x] SmolVLA(또는 폴백) MPS 로드 성공
- [x] claude -p 비전 검증 완료 (점수 기록)
- [x] `pytest tests/test_sprint0_*.py -v` 통과
- [x] `docs/progress/sprint-0.md` 작성

### 학습 자료
| 개념 | 왜 중요한가 | 레퍼런스 |
|------|------------|----------|
| MPS Backend | Apple Silicon GPU 가속 | [PyTorch MPS docs](https://pytorch.org/docs/stable/notes/mps.html) |
| SmolVLA 아키텍처 | 사용할 VLA 모델 이해 | [arXiv:2506.01844](https://arxiv.org/abs/2506.01844) |
| LeRobot 프레임워크 | VLA 모델 로딩/실행 방법 | [github.com/huggingface/lerobot](https://github.com/huggingface/lerobot) |
| claude -p headless | API 키 없이 LLM 호출 | [code.claude.com/docs/en/headless](https://code.claude.com/docs/en/headless) |
| Flow matching | SmolVLA의 액션 생성 방식 | SmolVLA 논문 Section 3 |

---

## Sprint 1: 시뮬레이션 환경 (~90분)

### 목표
Docker + ROS2 + Gazebo로 창고 환경(선반 3개, 물체 6개, 로봇 팔, 카메라) 구동.

### 태스크

**1.1 테스트 먼저 (10분)**
- `tests/test_sprint1_simulation.py`: Docker compose 유효성, 월드 파일 XML 검증, 선반/물체 수 확인

**1.2 Dockerfile + docker-compose.yml (15분)**
- 베이스: `osrf/ros:jazzy-desktop`
- 설치: `ros-jazzy-ros-gz`, `ros-jazzy-ros2-control`, `ros-jazzy-ros2-controllers`
- 포트: 5555, 5556 (ZMQ 브릿지), 11345 (Gazebo)
- 볼륨: 월드 파일, 컨피그 마운트
- 메모리 제한: `mem_limit: 6g`

**1.3 Docker 빌드 (20분, 백그라운드)**
- `docker compose -f docker/docker-compose.yml build`
- 이미지 풀 ~3GB, 병렬로 다른 작업 진행

**1.4 창고 SDF 월드 파일 (15분)**
- `src/simulation/worlds/warehouse.sdf`
- 바닥 + 선반 3개 (A, B, C) + 물체 6개 (apple, bottle, book, box, can, cup)
- 각 물체: 기본 기하학(구, 원통, 박스) + 물리(질량, 마찰)
- 수집 박스 + 오버헤드 카메라 + 조명

**1.5 로봇 팔 모델 + 제어 (15분)**
- Panda(Franka Emika) URDF 사용 또는 간소화 6-DOF 직접 정의
- `src/simulation/launch/warehouse.launch.py`: Gazebo 시작 + 로봇 스폰 + 컨트롤러 + 카메라
- `configs/robot.yaml`: 관절 한계, 홈 포지션, 그리퍼 파라미터

**1.6 카메라 + 이미지 캡처 (10분)**
- ROS2 카메라 토픽 확인, 스크린샷 저장

**1.7 통합 검증 + 보고서 (5분)**

### 완료 기준
- [x] Docker 컨테이너 빌드/실행 성공
- [x] Gazebo에 창고 월드 로드 (선반 3개 + 물체 6개)
- [x] 로봇 팔 스폰 + `ros2 topic pub`으로 제어 확인
- [x] 카메라 이미지 발행 확인
- [x] Gazebo 스크린샷 `docs/progress/`에 저장

### 폴백
| 리스크 | 폴백 |
|--------|------|
| Docker 이미지 풀 느림 | 레이어 캐시 활용, 이미지 축소 |
| Gazebo GPU 렌더링 안 됨 | `--headless-rendering` (소프트웨어) |
| 로봇 모델 Fuel에서 못 구함 | SDF에 직접 간소화 팔 정의 |
| macOS Docker 네트워킹 문제 | 파일 기반 브릿지 (공유 볼륨) |

### 학습 자료
| 개념 | 레퍼런스 |
|------|----------|
| Gazebo SDF 포맷 | [gazebosim.org/docs/harmonic](https://gazebosim.org/docs/harmonic/building_robot) |
| ROS2 launch 시스템 | [docs.ros.org/en/jazzy/Tutorials/Launch](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Creating-Launch-Files.html) |
| ros2_control | [control.ros.org/jazzy](https://control.ros.org/jazzy/index.html) |
| ros_gz_bridge | [github.com/gazebosim/ros_gz](https://github.com/gazebosim/ros_gz) |

---

## Sprint 2: VLA 통합 (~90분)

### 목표
SmolVLA가 macOS MPS에서 Gazebo 카메라 이미지를 받아 로봇 액션을 생성, 단일 pick-and-place 시도.

### 태스크

**2.1 테스트 먼저 (10분)**
- `tests/test_sprint2_executor.py`: 액션 변환기(shape, joint limits, scaling), VLA 노드(이미지 전처리, 추론)

**2.2 VLA 노드 구현 (20분)**
- `src/executor/vla_node.py`: SmolVLA 로딩, MPS 배치, 이미지 전처리, `predict(image, instruction) -> actions`
- `src/executor/models/model_loader.py`: SmolVLA/Octo/Scripted 로더

**2.3 액션 변환기 (15분)**
- `src/executor/action_converter.py`: VLA 정규화 출력[-1,1] → 실제 관절 각도, 관절 한계 클리핑, 그리퍼 매핑

**2.4 ZMQ 브릿지 (20분)**
- `src/simulation/bridge_docker.py`: Docker 내에서 ROS2 토픽 → ZMQ 발행
- `src/executor/bridge_host.py`: macOS에서 ZMQ 수신 → VLA 추론 → ZMQ로 명령 전송
- 폴백: 공유 볼륨 파일 기반 브릿지

**2.5 단일 pick-and-place 테스트 (20분)**
- `scripts/test_single_pick.py`: 카메라→VLA→명령→로봇 이동 확인

**2.6 검증 + 보고서 (5분)**

### 완료 기준
- [x] VLA(또는 폴백)가 MPS에서 Gazebo 이미지로 추론
- [x] 액션 변환기가 유효한 관절 명령 생성
- [x] 브릿지로 Docker↔Host 이미지/명령 전송 성공
- [x] 단일 pick 시도 (물체 방향으로 이동하면 성공)

### 학습 자료
| 개념 | 레퍼런스 |
|------|----------|
| SmolVLA 추론 API | [LeRobot examples](https://github.com/huggingface/lerobot/tree/main/examples) |
| VLA 액션 공간 | SmolVLA 논문 Table 1 |
| ZMQ pub/sub | [zeromq.org/get-started](https://zeromq.org/get-started/) |
| Sim-to-real gap (역방향) | OpenVLA 논문 Section 5.2 |

---

## Sprint 3: 에이전틱 오케스트레이터 (~90분)

### 목표
Planner + Verifier + Task Manager 상태 머신 통합, 단일 아이템 피킹 루프(계획→실행→검증) 동작.

### 태스크

**3.1 테스트 먼저 (15분)**
- `tests/test_sprint3_planner.py`: 주문 파싱, 피킹 계획, 재계획, claude -p 통합(모킹)
- `tests/test_sprint3_verifier.py`: 성공/실패 판단, 이유 반환
- `tests/test_sprint3_task_manager.py`: 모든 상태 전이, 잘못된 전이 거부, max retry, 전체 주문 완료

**3.2 공통 타입 (10분)**
- `src/common/types.py`: `TaskState` enum, `PickTask`, `VerificationResult`, `Order` dataclass

**3.3 Planner (15분)**
- `src/orchestrator/planner.py`: `parse_order()`, `plan()`, `replan()` — mock 모드 지원
- 프롬프트 템플릿: `prompts/planner_parse.txt`, `planner_plan.txt`, `planner_replan.txt`

**3.4 Verifier (15분)**
- `src/orchestrator/verifier.py`: `verify(image, expected_item, action) -> VerificationResult`
- 프롬프트 템플릿: `prompts/verifier_pick.txt`, `verifier_place.txt`

**3.5 Task Manager 상태 머신 (20분)**
- `src/orchestrator/task_manager.py`: PRD Section 5.3 상태 머신 구현
- 유효 전이 맵, retry 추적, 이벤트 콜백

**3.6 단일 아이템 피킹 루프 (10분)**
- `src/orchestrator/picking_loop.py`: Plan→Execute→Verify 통합 루프

**3.7 검증 + 보고서 (5분)**

### 완료 기준
- [x] Planner가 주문을 파싱하고 계획 생성 (모킹 + 실제 claude -p 1회)
- [x] Verifier가 구조화된 VerificationResult 반환
- [x] Task Manager 전체 상태 머신 동작
- [x] 단일 아이템 피킹 루프가 모킹으로 end-to-end 동작
- [x] `pytest tests/test_sprint3_*.py -v` 전체 통과

### 학습 자료
| 개념 | 레퍼런스 |
|------|----------|
| SayCan 어포던스 그라운딩 | [say-can.github.io](https://say-can.github.io/) |
| Inner Monologue 피드백 재계획 | [innermonologue.github.io](https://innermonologue.github.io/) |
| Agentic Robot (우리가 구현하는 것) | [arXiv:2505.23450](https://arxiv.org/abs/2505.23450) |
| FailSafe 실패 추론 | [arXiv:2510.01642](https://arxiv.org/abs/2510.01642) |

---

## Sprint 4: 오류 복구 + 멀티 아이템 (~60분)

### 목표
그립 실패 감지→재시도, 물체 낙하→재피킹, 멀티 아이템 순차 처리, max retry 초과 시 스킵.

### 태스크

**4.1 테스트 먼저 (10분)**
- `tests/test_sprint4_recovery.py`: 그립 실패 감지, 바닥 재피킹, 멀티 아이템 순차, 스킵+계속, 최종 보고서

**4.2 그립 실패 감지 (10분)** — Verifier에 `verify_grip()` 추가
**4.3 낙하 복구 (10분)** — Planner에 `pick_from_floor` 재계획 추가
**4.4 멀티 아이템 순차 처리 (15분)** — TaskManager에 태스크 큐 + `generate_report()`
**4.5 통합 테스트 (10분)** — 3-아이템 주문: 1성공, 1재시도성공, 1스킵
**4.6 검증 + 보고서 (5분)**

### 학습 자료
| 개념 | 레퍼런스 |
|------|----------|
| FailSafe 실패 분류 | [arXiv:2510.01642](https://arxiv.org/abs/2510.01642) |
| Self-Refining VLM | [arXiv:2602.12405](https://arxiv.org/html/2602.12405) |
| 자동 실패 복구 | [arXiv:2409.03966](https://arxiv.org/abs/2409.03966) |

---

## Sprint 5: 확장 + 데모 + 마무리 (~60분)

### 목표
CEO 확장 4개 구현, 벤치마크, README 작성.

### 태스크

**5.1 구조화된 로깅 + 리플레이 (10분)**
- `src/common/logger.py` 완성: `StructuredLogger`, JSONL 출력
- `scripts/replay.py`: 로그 파일에서 실행 타임라인 재생

**5.2 LLM 추론 트레이스 UI (10분)**
- `src/orchestrator/reasoning_trace.py`: claude -p 원문 캡처 + rich 라이브러리로 컬러 터미널 출력

**5.3 A/B 비교 시각화 (10분)**
- `scripts/benchmark.py`: VLA-only vs Agent+VLA 비교 실행
- `scripts/visualize_comparison.py`: matplotlib 바 차트 → `docs/assets/ab_comparison.png`

**5.4 인터랙티브 방해 데모 (10분)**
- `scripts/demo_adversarial.py`: 피킹 중 Gazebo 서비스로 물체 텔레포트 → 로봇 감지→재계획→복구

**5.5 벤치마크 실행 (5분)**
**5.6 README + 아키텍처 다이어그램 (10분)**
- `README.md`: 제목, 아키텍처 다이어그램, 데모 GIF, 주요 기능, Quick Start, 벤치마크 결과, 기술 스택, 레퍼런스
- `docs/ARCHITECTURE.md`: 상세 데이터 플로우

**5.7 최종 검증 (5분)**: `pytest tests/ -v`, `bash scripts/demo.sh`

### 학습 자료
| 개념 | 레퍼런스 |
|------|----------|
| LIBERO 벤치마크 방법론 | Agentic Robot 논문 평가 섹션 |
| A/B 테스팅 for 로보틱스 | Agentic Robot 논문 비교 실험 |

---

## 전체 파일 인벤토리 (~61개 파일)

| Sprint | 파일 수 | 주요 파일 |
|--------|---------|----------|
| 0 | 12 | `pyproject.toml`, `src/common/types.py`, `tests/test_sprint0_*.py` |
| 1 | 8 | `docker/Dockerfile`, `warehouse.sdf`, `warehouse.launch.py` |
| 2 | 8 | `vla_node.py`, `action_converter.py`, `bridge_host.py` |
| 3 | 13 | `planner.py`, `verifier.py`, `task_manager.py`, 프롬프트 5개 |
| 4 | 5 | 복구 프롬프트 2개, `test_sprint4_*.py` |
| 5 | 9 | `benchmark.py`, `README.md`, `demo.sh` |
| 보고서 | 6 | `docs/progress/sprint-{0-5}.md` |

---

## 자기 전 체크리스트

1. [ ] Docker Desktop 실행 중 확인
2. [ ] `scripts/overnight.sh` 생성 및 실행 권한 부여
3. [ ] `nohup bash scripts/overnight.sh > overnight.log 2>&1 &` 실행
4. [ ] 맥북 슬립 방지 설정 (System Settings → Energy → Prevent sleep)
5. [ ] 충전기 연결 확인
