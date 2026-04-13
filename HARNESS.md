# Harness Engineering

오버나이트 랄프톤은 **모델 성능**보다 **하네스**가 성패를 가른다. 같은 Claude가 돌아도, 어떤 도구·훅·스킬·프롬프트 구조로 감쌌는지에 따라 결과가 10배 차이 난다. 이 문서는:

1. 하네스 엔지니어링의 핵심 원칙
2. 이 레포에서 쓸 수 있는 도구 카탈로그
3. 각 챌린지마다 "이번엔 어떻게 하네스를 짰는지" 기록하는 템플릿

---

## 1. 핵심 원칙

### 1.1 모델이 아니라 하네스를 설계한다
모델은 블랙박스 상수다. 내가 통제할 수 있는 건 **입력(프롬프트·컨텍스트)**, **도구(tool surface)**, **루프(실행 구조)**, **검증(verifier)** 네 레이어뿐이다. 하네스 엔지니어링 = 이 네 레이어를 목적에 맞게 재단하는 일.

### 1.2 작은 surface가 강하다
도구 50개 주면 모델이 헤맨다. 한 챌린지에는 정말 필요한 도구만 노출. OMC 에이전트도 마찬가지 — `executor` 하나로 충분한 걸 `planner→architect→critic` 풀체인으로 돌리면 토큰만 태우고 품질 안 늘어남.

### 1.3 검증은 생성과 분리된 레인에서
같은 세션에서 "만들고 스스로 검토"시키면 confirmation bias가 터진다. **쓰는 에이전트 ≠ 승인하는 에이전트** (OMC `<execution_protocols>`에 박혀 있음). `code-reviewer`, `verifier`, 외부 `pytest` — 뭐가 됐든 다른 레인.

### 1.4 루프는 자기복구형으로
리밋·에러·모호성 중 하나라도 멈춤이면 오버나이트는 죽는다. 각 세션은 **checkpoint script**로 성공/실패 판정 후 다음으로 넘어가는 구조. 단일 `claude -p` 호출에 의존하지 말 것.

### 1.5 컨텍스트는 상시 압축
`CLAUDE.md`(영구), `challenge-N/TIMELINE.md`(세션 간), OMC `notepad.md`(컴팩션 내성) — 세 층으로 나눠서 중요한 정보가 증발하지 않게.

### 1.6 모든 결정은 기록된다
프롬프트 원문, 세션 로그, 분기 결정 근거 — 전부 파일로 커밋. "밤에 뭐 한 거지?" 물음에 `git log`와 `challenge-N/`만 보면 재구성 가능해야 함.

---

## 2. 도구 카탈로그 (이 레포에서 사용 가능)

### Claude Code 본체
- **Hooks** (`settings.json`) — 이벤트 훅으로 자동 동작. 예: 커밋 후 테스트, PreToolUse로 위험 명령 차단.
- **Skills** (`/<skill-name>`) — 재사용 가능한 워크플로우. 슬래시 명령.
- **Sub-agents** — 격리된 컨텍스트에서 전문 역할 수행. 토큰 절약 + 병렬.
- **MCP 서버** — 외부 도구 연결 (Gmail, Notion, Excalidraw 등 현재 붙어있음).
- **Plan Mode** / **Worktree** / **Background tasks** — 설계/격리/비동기.

### OMC (oh-my-claudecode) — 현재 설치됨
워크플로우 레이어.
- **Tier-0 루프**: `autopilot`, `ultrawork`, `ralph`, `ralplan`, `team`
- **검증/리뷰**: `code-review`, `security-review`, `critic`, `verifier`
- **에이전트 역할**: `planner`, `architect`, `executor`, `explore`, `writer`, `designer`
- **모델 라우팅**: haiku(빠름) / sonnet(기본) / opus(깊은 분석)
- **킬 스위치**: `DISABLE_OMC`, `OMC_SKIP_HOOKS` 환경변수

상세는 `.claude/CLAUDE.md` 참조 (레포에 커밋됨).

### 외부 도구 (선택적)
- **gstack** — 헤드리스 브라우저 QA. 웹 챌린지일 때만.
- **Superpower / Codex CLI** — 2차 의견용 독립 리뷰어.
- **쉘 wrapper** — Claude 자체의 리밋/에러를 감싸는 바깥 루프. `PLAYBOOK.md` §3 템플릿.

### 프롬프트 구조
- **사전 문서** (`PRD.md`, `EXECUTION_PLAN.md`, `TECH_STACK.md`) — 세션마다 읽히는 정적 컨텍스트
- **세션 프롬프트** (`prompts/session-N.txt`) — 동적 지시
- **System reminders** (훅 주입) — 런타임 규칙 강제

---

## 3. 챌린지별 하네스 기록 템플릿

각 `challenge-N/`에 `HARNESS.md`를 두고 아래 양식을 채운다. 회고 때 "뭐가 먹혔고 뭐가 안 먹혔나"를 가르는 자료.

```markdown
# challenge-N Harness

## 도구 선택
| 레이어 | 사용한 것 | 왜 |
|--------|----------|-----|
| 루프 | 예: OMC ralph / 자체 overnight.sh | 이 챌린지에 왜 이걸 골랐나 |
| 에이전트 | 예: executor(opus) + code-reviewer | |
| 검증 | 예: pytest + OMC verifier | |
| 외부 도구 | 예: gstack (웹 QA), 없음 | |
| 훅 | 예: PostToolUse로 pytest 자동 | |

## 프롬프트 설계
- 사전 문서: [어떤 파일을 사전에 썼는지]
- 세션 분할: [세션 N개로 쪼갰고 각자 무엇 담당]
- 컨텍스트 경계: [Claude가 뭘 읽고 뭘 안 읽게 했는지]

## 리밋 대응
- 재시도 정책: [sleep 시간, 재시도 횟수]
- Checkpoint 기준: [다음 세션으로 넘어가는 성공 조건]

## 실측 결과 (회고 때 채움)
- 리밋 발동 횟수:
- 자동 재개 성공률:
- 사람 개입 필요했던 지점:
- 다음 챌린지에 가져갈 것:
- 다음 챌린지에 버릴 것:
```

---

## 4. 하네스 체크리스트 (챌린지 시작 전)

- [ ] `challenge-N/HARNESS.md` 작성 (도구 선택 이유 명시)
- [ ] 검증 레인이 생성 레인과 분리되어 있나?
- [ ] Checkpoint 스크립트로 세션 간 성공 판정하나?
- [ ] 리밋 회복 루프가 쉘 레벨에 있나? (Claude 내부 재시도 ≠ 리밋 회복)
- [ ] `CLAUDE.md`의 8개 원칙 모두 프롬프트/훅으로 강제되나?
- [ ] 사용자가 밤에 깨서 답해야 할 질문이 0개인가?

이 문서 자체도 회고 반영 대상 — 챌린지마다 업데이트.
