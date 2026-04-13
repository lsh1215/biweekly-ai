# biweekly-ai — Repo Rules

이 레포는 2주에 한 번 "자기 전 2~3시간 문서 작성 → 자는 동안 Claude 자율 실행 → 기상 후 검증" 사이클로 돌아가는 **오버나이트 랄프톤** 레포다. 각 사이클은 `challenge-N/` 디렉토리 하나로 자급자족한다.

## Claude가 새 챌린지를 시작할 때 지켜야 할 규칙

오버나이트 실행 중 스스로 지킬 것. 사용자는 자고 있다.

### 불변 원칙 (challenge-1 회고에서 확정)

1. **무인 실행**: 사용자에게 질문·확인 요청 금지. 모호하면 자체 결정하고 `challenge-N/TIMELINE.md`에 "왜 그 선택을 했는지" 기록하고 진행.
2. **TDD 강제**: 스프린트마다 **테스트 파일 먼저**, 구현 나중. 테스트 통과 없이 다음 스프린트로 넘어가지 말 것.
3. **1-command 검증 가능**: `challenge-N/VERIFY.md`(설명) + `challenge-N/VERIFY.sh`(실행) 없이는 챌린지 완료로 간주하지 않음. 기상한 사용자가 첫 5분 안에 결과를 재현할 수 있어야 함.
4. **프롬프트 로그 보존**: `challenge-N/prompts/session-N.txt`(사전 작성)와 `challenge-N/logs/*.log`(실행 기록) 모두 커밋. 회고 자료.
5. **TIMELINE.md 실시간 갱신**: 스프린트 시작/종료/이슈/결정을 ISO 타임스탬프로 append. 기상 후 사용자가 이것만 보면 밤 사이 상황 파악 완료.
6. **커밋 단위 = 스프린트 단위**: 스프린트 끝 = 테스트 통과 = 커밋. 롤백 단위 보장.
7. **절대경로 하드코딩 금지**: 스크립트는 `"$(dirname "$0")/.."` 같은 상대 기준. 레포·디렉토리 이름 바뀌어도 깨지지 말 것.
8. **랄프톤 부적합 주제 경고**: 사용자가 외부 API/GPU/시뮬레이터 의존이 강한 주제를 제시하면, 작업 시작 전 `challenge-N/PRD.md` 상단에 위험 요소와 대안(mock/CPU 폴백)을 명시.

### 리밋 대응 (중요)

Claude 사용량 리밋에 걸리면 오버나이트가 죽는다. 대응:

- 각 세션은 외부 쉘 루프 (`challenge-N/scripts/overnight.sh`) 안에서 실행. 리밋 감지 시 5시간 10분 대기 후 자동 재시도. 템플릿은 `PLAYBOOK.md` §3 참조.
- 또는 OMC `/oh-my-claudecode:ralph` 사용 (자기복제 루프 + 아키텍트 검증 내장).
- 단순 `sleep 900` 같은 경험값 금지 — 리밋 회복 안 될 수 있음.

### 새 챌린지 디렉토리 초기화

사용자가 "challenge-N 시작" 류의 지시를 하면:

```
challenge-N/
├── PRD.md              # 뭘/왜/성공기준
├── EXECUTION_PLAN.md   # 스프린트 분할
├── TECH_STACK.md       # 기술 선택
├── VERIFY.md           # 재현 절차
├── VERIFY.sh           # 재현 스크립트
├── TIMELINE.md         # 비어있음 (실행 중 채움)
├── prompts/session-0.txt ... session-N.txt
├── scripts/overnight.sh
├── scripts/checkpoint_sprint0.sh ...
└── logs/               # .gitkeep
```

템플릿 내용은 `PLAYBOOK.md` 참조.

### 회고 반영

챌린지 종료 시 `challenge-N/RETRO.md` 작성 후, 여기서 얻은 교훈은 **이 파일(`CLAUDE.md`)과 `PLAYBOOK.md`를 직접 수정해서** 차기 챌린지에 자동 반영. 회고만 쌓고 규칙을 안 바꾸면 같은 실수 반복.

## 참고 문서

- `PLAYBOOK.md` — 오버나이트 프로토콜 상세 (주제 선정, 자동 재개 템플릿, 검증)
- `challenge-1/RETRO.md` — 첫 번째 회고 (VLA 프로젝트)

## OMC 관련

`.claude/CLAUDE.md`에 oh-my-claudecode 오케스트레이션 규칙이 별도로 있음. 이 파일의 규칙이 OMC 규칙과 충돌할 때는 **이 파일 우선** (챌린지 진행 규칙이 도구 사용 규칙보다 상위).
