# Warehouse Picker — 기술 스택 및 참고 자료

> 최종 업데이트: 2026-03-29

## 1. 프로젝트 개요

**Warehouse Picker**: VLA(Vision-Language-Action) 모델 기반 에이전틱 물류 피킹 로봇 시스템.
LLM 오케스트레이터가 주문을 해석하고 피킹 계획을 수립하며, VLA 모델이 로봇 팔로 물건을 피킹하고,
비전 기반 검증기가 피킹 결과를 모니터링하여 실패 시 재계획하는 구조.

```
주문 입력 ("사과 1개, 물병 1개")
       │
       ▼
┌──────────────────────────────┐
│  Planner (claude -p, 구독)   │ ← 주문 파싱 / 피킹 계획 / 오류 재계획
└──────────┬───────────────────┘
           │ 서브태스크 ("선반 A3에서 사과를 집어")
           ▼
┌──────────────────────────────┐
│  Executor (SmolVLA + MPS)    │ ← 로봇 액션 생성 (관절 각도, 그리퍼)
└──────────┬───────────────────┘
           │ ROS2 JointCommand
           ▼
┌──────────────────────────────┐
│  Simulator (Gazebo Harmonic) │ ← 창고 환경 시뮬레이션 (선반, 물체, 로봇)
└──────────┬───────────────────┘
           │ RGB-D 카메라 피드백
           ▼
┌──────────────────────────────┐
│  Verifier (claude -p, 비전)  │ ← 피킹 성공/실패 판단 → 실패 시 Planner 복귀
└──────────────────────────────┘
```

---

## 2. 기술 스택

### 2.1 에이전틱 오케스트레이터

| 항목 | 선택 | 비고 |
|---|---|---|
| **LLM** | `claude -p` (Claude Max 구독) | API 키 불필요, 구독 요금으로 실행 |
| **역할** | Planner + Verifier | SayCan, Inner Monologue 패턴 기반 |
| **호출 방식** | `claude -p --output-format json` | 구조화된 JSON 출력으로 파싱 |
| **호출 빈도** | 서브태스크 단위 (저빈도) | 실시간 제어에는 사용하지 않음 |
| **비전 입력** | Verifier에서 RGB 이미지 전달 | 피킹 성공/실패 시각적 판단 |

#### 구독 기반 실행 설정 (API 키 불필요)

```bash
# 핵심: ANTHROPIC_API_KEY가 설정되어 있으면 반드시 해제
unset ANTHROPIC_API_KEY

# Claude 로그인 (최초 1회)
claude auth login

# Planner 호출 예시
claude -p "주문: 사과(A3), 물병(B2). 피킹 계획을 JSON으로 세워줘" \
  --output-format json | jq -r '.result'

# Verifier 호출 예시 (이미지 포함)
claude -p "이 이미지를 보고 사과를 성공적으로 집었는지 판단해줘" \
  --output-format json
```

#### 대안 실행 방식 (참고)

| 방식 | 구독 사용 | 용도 |
|---|---|---|
| `claude -p` (채택) | ✅ | 스크립트/자동화, 가장 심플 |
| Claude Agent SDK + OAuth | ✅ | Python 프로그램 내 에이전틱 루프 |
| Claude API + API Key | ❌ (별도 과금) | 대량 호출, 프로덕션 |
| Meridian (로컬 프록시) | ✅ | Anthropic API 호환 도구 연동 |

### 2.2 VLA 모델

| 항목 | 선택 | 비고 |
|---|---|---|
| **모델** | SmolVLA (450M) | HuggingFace/LeRobot, 맥북 추론 가능 |
| **프레임워크** | PyTorch + MPS 백엔드 | Apple Silicon GPU 가속 |
| **출력** | 로봇 액션 (관절 각도, 그리퍼 제어) | Flow matching 기반 연속 액션 |
| **대안 (스케일업)** | OpenVLA (7B), π0 (3B) | GPU 클라우드 환경에서 전환 가능 |

#### VLA 모델 비교 (참고)

| 모델 | 파라미터 | 오픈소스 | 액션 타입 | 맥북 추론 |
|---|---|---|---|---|
| SmolVLA | 450M | ✅ | Flow matching | ✅ |
| Octo | ~90M | ✅ | Diffusion | ✅ |
| OpenVLA | 7B | ✅ | Discrete tokens | ⚠️ 양자화 필요 |
| OpenVLA-OFT | 7B | ✅ | Chunked parallel | ⚠️ 양자화 필요 |
| π0 (pi-zero) | ~3B | ✅ | Flow matching (50Hz) | ⚠️ 가능하나 느림 |
| GR00T N1 | 2.2B | ✅ | Diffusion flow | ❌ CUDA 필요 |
| RT-2 | 55B | ❌ | Discrete tokens | ❌ |

### 2.3 시뮬레이션 환경

| 항목 | 선택 | 비고 |
|---|---|---|
| **시뮬레이터** | Gazebo Harmonic | 업계 표준, ROS2 Jazzy 페어링 |
| **미들웨어** | ROS2 Jazzy (LTS) | 로보틱스 업계 공통 프레임워크 |
| **물리 엔진** | DART | Gazebo 기본 엔진 |
| **실행 환경** | Docker (로컬 맥북) | `osrf/ros:jazzy-desktop` 이미지 |

#### 시뮬레이터 선택 근거

| 기준 | Gazebo | Isaac Sim | 선택 이유 |
|---|---|---|---|
| 업계 채택도 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 포트폴리오 목적에 Gazebo 적합 |
| 맥북 호환 | ✅ | ❌ (RTX 필수) | 하드웨어 제약 |
| ROS2 통합 | 네이티브 | 브릿지 | Gazebo가 ROS2와 가장 긴밀 |
| 라이선스 | Apache 2.0 | 연구용 무료 (제한) | 오픈소스 선호 |
| Docker 이미지 | ~3 GB | ~15 GB | 가벼움 |

### 2.4 개발 환경

| 항목 | 선택 | 비고 |
|---|---|---|
| **하드웨어** | MacBook Pro M2 Pro 32GB | 통합 메모리, MPS GPU 가속 |
| **컨테이너** | Docker Desktop for Mac | Gazebo + ROS2 실행 |
| **언어** | Python | VLA 추론, 에이전트 로직, ROS2 노드 |
| **ML 프레임워크** | PyTorch (MPS 백엔드) | Apple Silicon 가속 |
| **VLA 프레임워크** | HuggingFace LeRobot | SmolVLA 로딩 및 추론 |

### 2.5 스케일업 경로 (GPU 확보 시)

| 단계 | 환경 | 추가 가능 항목 |
|---|---|---|
| 현재 | 맥북 M2 Pro | SmolVLA + Gazebo + `claude -p` (구독) |
| 클라우드 GPU (A100) | RunPod / Lambda Labs | OpenVLA 파인튜닝, ManiSkill3 병렬 학습 |
| RTX GPU (4090) | 로컬 또는 클라우드 | Isaac Sim 포토리얼 데이터 생성 |

---

## 3. 아키텍처 패턴

### 3.1 Hierarchical VLA (채택)

LLM이 고수준 계획을 수립하고 VLA가 저수준 실행을 담당하는 계층적 구조.
Agentic Robot 논문(2025)에서 검증된 Planner-Executor-Verifier 3단 구조를 기반으로 함.

```
Planner (LLM) → Executor (VLA) → Verifier (VLM)
                    ↑                    │
                    └── 실패 시 재계획 ←─┘
```

- LIBERO 벤치마크에서 79.6% 성공률 (VLA 단독 대비 +7.4%)

### 3.2 대안 패턴 (참고)

| 패턴 | 설명 | 대표 논문 |
|---|---|---|
| End-to-End VLA | 단일 모델이 전체 처리 | π0, π0.5 |
| Code as Policies | LLM이 Python 코드로 로봇 제어 | Liang et al., 2023 |
| VoxPoser | LLM이 3D 어포던스 맵 생성 | Huang et al., 2023 |
| System 1/2 (Dual) | 빠른 반사 + 느린 추론 이중 시스템 | GR00T N1, PsiBot |
| Brain-Cerebellum | 뇌(MLLM) + 소뇌(스킬 라이브러리) | RoboOS |

---

## 4. 참고 논문

### 4.1 VLA 모델 핵심 논문

| 논문 | 연도 | 링크 | 핵심 기여 |
|---|---|---|---|
| RT-2: Vision-Language-Action Models | 2023 | [arXiv:2307.15818](https://arxiv.org/abs/2307.15818) | 최초 대규모 VLA, PaLM-E 기반 |
| Octo: Open-Source Generalist Robot Policy | 2024 | [arXiv:2405.12213](https://arxiv.org/abs/2405.12213) | 오픈소스, 크로스 로봇 일반화 |
| OpenVLA: Open-Source Vision-Language-Action Model | 2024 | [arXiv:2406.09246](https://arxiv.org/abs/2406.09246) | 7B 오픈소스 VLA 베이스라인 |
| OpenVLA-OFT: Optimized Fine-Tuning | 2025 | [openvla-oft.github.io](https://openvla-oft.github.io/) | 26x 빠른 액션 생성 |
| π0: Vision-Language-Action Flow Model | 2024 | [arXiv:2410.24164](https://arxiv.org/abs/2410.24164) | Flow matching, 50Hz, 정교한 조작 |
| π0.5: Open-World Generalization | 2025 | [pi.website](https://www.pi.website/download/pi05.pdf) | 새로운 환경 일반화 |
| GR00T N1: Humanoid Robot Foundation Model | 2025 | [arXiv:2503.14734](https://arxiv.org/abs/2503.14734) | 이중 시스템, 2.2B 오픈 |
| SmolVLA: Affordable and Efficient Robotics | 2025 | [arXiv:2506.01844](https://arxiv.org/abs/2506.01844) | 450M, 소비자 하드웨어 |

### 4.2 에이전틱 로보틱스 핵심 논문

| 논문 | 연도 | 링크 | 핵심 기여 |
|---|---|---|---|
| SayCan: Grounding Language in Robotic Affordances | 2022 | [say-can.github.io](https://say-can.github.io/) | LLM + 어포던스 그라운딩 |
| Inner Monologue: Embodied Reasoning with LMs | 2022 | [innermonologue.github.io](https://innermonologue.github.io/) | 피드백 기반 LLM 재계획 |
| Code as Policies: Language Model Programs for Robotics | 2023 | [arXiv:2209.07753](https://arxiv.org/abs/2209.07753) | LLM이 실행 코드 생성 |
| VoxPoser: Composable 3D Value Maps | 2023 | [arXiv:2307.05973](https://arxiv.org/abs/2307.05973) | 3D 어포던스 맵 |
| Agentic Robot: Brain-Inspired VLA Framework | 2025 | [arXiv:2505.23450](https://arxiv.org/abs/2505.23450) | Planner+VLA+Verifier 검증 |
| RoboOS: Hierarchical Embodied Framework | 2025 | [arXiv:2505.03673](https://arxiv.org/abs/2505.03673) | Brain-Cerebellum 구조 |
| SELF-VLA: Skill Enhanced Agentic VLA | 2025 | [arXiv:2603.11080](https://arxiv.org/html/2603.11080v1) | 접촉 조작 스킬 라이브러리 |
| ManiAgent: Multi-agent Manipulation | 2025 | [arXiv:2510.11660](https://arxiv.org/abs/2510.11660) | 멀티에이전트 조작 |

### 4.3 오류 복구 / 자기 교정

| 논문 | 연도 | 링크 | 핵심 기여 |
|---|---|---|---|
| FailSafe: Reasoning and Recovery from VLA Failures | 2025 | [arXiv:2510.01642](https://arxiv.org/abs/2510.01642) | 실패 생성 + 복구 |
| Self-Refining VLM for Failure Detection | 2025 | [arXiv:2602.12405](https://arxiv.org/html/2602.12405) | VLM 자기 개선 |
| Automating Failure Recovery with VLMs | 2024 | [arXiv:2409.03966](https://arxiv.org/abs/2409.03966) | 자동 실패 복구 |

### 4.4 서베이 논문

| 논문 | 연도 | 링크 |
|---|---|---|
| VLA Models for Robotics: A Review (IEEE) | 2025 | [arXiv:2510.07077](https://arxiv.org/abs/2510.07077) |
| Pure VLA Models: Comprehensive Survey | 2025 | [arXiv:2509.19012](https://arxiv.org/abs/2509.19012) |
| LLM+VLM Driven Robot Autonomy | 2025 | [arXiv:2508.05294](https://arxiv.org/abs/2508.05294) |
| VLA Models: Concepts, Progress, Challenges | 2025 | [arXiv:2505.04769](https://arxiv.org/abs/2505.04769) |

---

## 5. 필수 읽기 순서

1. **SayCan** — LLM이 로봇 어포던스를 고려해 계획을 세우는 원리
2. **Inner Monologue** — 환경 피드백으로 LLM이 재계획하는 구조
3. **OpenVLA** — 현재 오픈소스 VLA 베이스라인 이해
4. **SmolVLA** — 실제 사용할 모델의 아키텍처와 성능
5. **Agentic Robot** — 이 프로젝트와 가장 유사한 Planner+VLA+Verifier 구현
6. **FailSafe** — 오류 복구 루프 설계

---

## 6. 주요 GitHub 레포지토리

| 레포 | 설명 | 링크 |
|---|---|---|
| **HuggingFace LeRobot** | VLA 통합 프레임워크 (SmolVLA 포함) | [github.com/huggingface/lerobot](https://github.com/huggingface/lerobot) |
| **OpenVLA** | 7B 오픈소스 VLA | [github.com/openvla/openvla](https://github.com/openvla/openvla) |
| **OpenPI (π0)** | Physical Intelligence 오픈 릴리즈 | [github.com/Physical-Intelligence/openpi](https://github.com/Physical-Intelligence/openpi) |
| **Agentic-Robot** | Planner+VLA+Verifier 구현체 | [github.com/Agentic-Robot/agentic-robot](https://github.com/Agentic-Robot/agentic-robot) |
| **RoboOS** | 계층적 로봇 OS 프레임워크 | [github.com/FlagOpen/RoboOS](https://github.com/FlagOpen/RoboOS) |
| **VoxPoser** | 3D 어포던스 맵 생성 | [github.com/huangwl18/VoxPoser](https://github.com/huangwl18/VoxPoser) |
| **Isaac-GR00T** | NVIDIA 휴머노이드 파운데이션 모델 | [github.com/NVIDIA/Isaac-GR00T](https://github.com/NVIDIA/Isaac-GR00T) |
| **Awesome-LLM-Robotics** | LLM+로보틱스 논문 큐레이션 | [github.com/GT-RIPL/Awesome-LLM-Robotics](https://github.com/GT-RIPL/Awesome-LLM-Robotics) |

---

## 7. Warehouse Picker 도메인 참고 자료

### 7.1 물류 피킹 로봇 관련 논문/프로젝트

| 자료 | 설명 | 링크 |
|---|---|---|
| RoboCasa | 가정/주방 환경 360+ 태스크, MuJoCo 기반 | [robocasa.ai](https://robocasa.ai/) |
| RoboVerse | 멀티 시뮬레이터 통합 플랫폼 (1,000+ 태스크) | [arXiv:2504.18904](https://arxiv.org/abs/2504.18904) |
| LIBERO | 장기 로봇 매니퓰레이션 벤치마크 (Agentic Robot 검증용) | LIBERO benchmark |
| Meta-World | 50개 매니퓰레이션 태스크 (LeRobot 지원) | Meta-World |

### 7.2 Gazebo 창고 환경 구축 참고

| 자료 | 설명 |
|---|---|
| Gazebo Fuel Models | 커뮤니티 로봇/환경 모델 (fuel.gazebosim.org) |
| ros2_control + Gazebo | ROS2 로봇 제어 통합 |
| MoveIt2 | ROS2 모션 플래닝 (피킹 궤적 생성 대안) |
| gazebo_ros2_control | Gazebo-ROS2 하드웨어 인터페이스 |

### 7.3 `claude -p` 오케스트레이터 구현 참고

| 자료 | 설명 | 링크 |
|---|---|---|
| Claude Code 프로그래밍 사용법 | `claude -p` 공식 문서 | [code.claude.com/docs/en/headless](https://code.claude.com/docs/en/headless) |
| Claude Code 인증 | 구독 기반 인증 설정 | [code.claude.com/docs/en/authentication](https://code.claude.com/docs/en/authentication) |
| GitHub Issue #37686 | API 키 vs 구독 과금 주의사항 | [github.com/anthropics/claude-code/issues/37686](https://github.com/anthropics/claude-code/issues/37686) |

---

## 8. 한국 관련 연구/기업

| 이름 | 유형 | 설명 |
|---|---|---|
| **RLWRLD** | 스타트업 | 로봇 파운데이션 모델, $41M 투자 (LG, SK) |
| **KAIST NAIRL** | 연구소 | 국가 AI 연구소, VLA 추론 연구 |
| **POSTECH DSLab** | 연구실 | 로봇 파운데이션 모델, 모바일 매니퓰레이션 |
| **KAIST IRIS** | 연구실 | 인간-로봇 상호작용 |
| **K-Humanoid Alliance** | 정부 사업 | 휴머노이드 로봇 + AI 국가 프로젝트 |
