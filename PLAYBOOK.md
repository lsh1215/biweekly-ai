# Biweekly AI Ralph-thon Playbook

2주에 한 번, 2~3시간 사전 문서 작성 → 자는 동안 자율 실행 → 기상 후 검증.
Challenge-1(VLA) 회고에서 도출된 실전 프로토콜.

---

## 1. 주제 선정 체크리스트

랄프톤에 **적합한** 주제:
- [ ] 외부 API/서비스 의존 최소 (있으면 mock 우선)
- [ ] GPU/특수 하드웨어 없이도 CPU로 검증 가능
- [ ] 결과물을 1-command로 재현 가능 (`bash VERIFY.sh`, `pytest`, URL 접속 등)
- [ ] 스프린트 단위로 쪼갤 수 있음 (한 세션 = 한 스프린트)
- [ ] 실패해도 다음 스프린트가 독립 진행 가능

**부적합 신호**: Docker+시뮬레이터+ML 모델이 모두 엮인 체인, 수동 사람 판단이 중간에 필요, 결과 검증에 도메인 지식 깊게 필요.

---

## 2. 사전 문서 템플릿 (자기 전 2~3시간)

`challenge-N/` 안에 다음 파일을 **반드시** 둔다:

| 파일 | 역할 |
|------|------|
| `PRD.md` | 뭘 만드는지, 왜, 성공 기준 |
| `EXECUTION_PLAN.md` | Sprint 0~N, 각 스프린트 목표/테스트/폴백 |
| `TECH_STACK.md` | 사용 기술, 로컬/Docker 분담 |
| `VERIFY.md` | **기상 후 결과 재현 절차** (1-command 우선) |
| `prompts/session-N.txt` | 각 세션에 Claude에 줄 프롬프트 원문 |
| `TIMELINE.md` | 비어둠 — Claude가 실행하며 채움 |

`VERIFY.md`가 제일 중요. 웹이면 URL + 시나리오, 아니면 명령어 + 기대 출력.

---

## 3. 오버나이트 실행 프로토콜

### 핵심 3원칙

1. **무인 실행**: 도중에 사용자 입력 요구 금지. 모호하면 Claude가 결정·기록·진행
2. **촘촘한 테스트**: 스프린트마다 `pytest` (또는 등가) 통과가 커밋 조건
3. **자동 재개**: Claude 5시간 리밋 걸리면 해제 시각까지 대기 후 자동 재시도

### 자동 재개 루프 (권장 템플릿)

`challenge-N/scripts/overnight.sh`:

```bash
#!/bin/bash
set -u
cd "$(dirname "$0")/.."           # 절대경로 하드코딩 금지
CHALLENGE_DIR="$(pwd)"
LOG_DIR="$CHALLENGE_DIR/logs"
mkdir -p "$LOG_DIR"

run_session() {
  local name="$1" prompt_file="$2" max_turns="${3:-100}"
  local attempt=0
  while (( attempt < 5 )); do
    attempt=$((attempt+1))
    echo "[$(date -Iseconds)] session=$name attempt=$attempt" | tee -a "$LOG_DIR/timeline.log"

    claude -p --dangerously-skip-permissions \
      --max-turns "$max_turns" \
      "$(cat "$prompt_file")" \
      > "$LOG_DIR/${name}.attempt${attempt}.log" 2>&1
    local rc=$?

    if grep -qE "usage limit|rate.?limit|quota" "$LOG_DIR/${name}.attempt${attempt}.log"; then
      # 5시간 + 10분 버퍼 대기 후 재시도
      echo "[$(date -Iseconds)] $name hit limit, sleeping 5h10m" | tee -a "$LOG_DIR/timeline.log"
      sleep 18600
      continue
    fi

    if [[ $rc -eq 0 ]] && bash "$CHALLENGE_DIR/scripts/checkpoint_${name}.sh"; then
      echo "[$(date -Iseconds)] $name OK" | tee -a "$LOG_DIR/timeline.log"
      return 0
    fi

    # 일반 실패 → 짧게 쉬고 재시도
    sleep 300
  done
  echo "[$(date -Iseconds)] $name FAILED after $attempt attempts" | tee -a "$LOG_DIR/timeline.log"
  return 1
}

run_session "sprint0" "$CHALLENGE_DIR/prompts/session-0.txt" 80 || exit 1
run_session "sprint1" "$CHALLENGE_DIR/prompts/session-1.txt" 120 || exit 1
run_session "sprint2" "$CHALLENGE_DIR/prompts/session-2.txt" 120 || exit 1
# ...
```

각 `scripts/checkpoint_sprintN.sh`는 "이 스프린트 진짜 됐는지" 확인 (예: `pytest tests/test_sprintN* && test -f docs/progress/sprint-N.md`).

### 프롬프트 로그 (회고 자료)

`prompts/session-N.txt`는 **사전에 완성**해서 커밋. Claude가 세션마다 어떤 프롬프트를 받았는지 기록이 남아야 다음 회고가 가능. 실행 로그는 `logs/sprint-N.attemptM.log`에 타임스탬프로 축적.

### 대안: OMC Ralph 스킬

이 레포는 OMC가 설정돼 있으므로 수동 루프 대신 `/oh-my-claudecode:ralph`를 쓰면 자기복제 루프 + 아키텍트 검증이 붙은 형태로 같은 효과를 낼 수 있음. 단, 외부 세션 재개(리밋 회복)는 여전히 상위 쉘 루프 필요.

---

## 4. 기상 후 검증

```bash
cd challenge-N
cat TIMELINE.md        # 뭐가 일어났는지
cat logs/timeline.log  # 세션별 성공/실패
bash VERIFY.sh         # 결과물 1-command 재현
```

`VERIFY.sh` 없으면 랄프톤 실패로 간주 (다음 회고에 기록).

---

## 5. 회고 (챌린지 종료 시)

`challenge-N/RETRO.md` 작성:
- 진행 타임라인 (`logs/timeline.log` 기반)
- 잘된 점 / 문제점 / 아쉬운 점
- 교훈 → 이 `PLAYBOOK.md`와 루트 `CLAUDE.md`를 **직접 수정**해서 차기 챌린지에 반영

반영 안 하면 같은 실수를 반복한다.
