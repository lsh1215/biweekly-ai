# challenge-3 RETRO

(skeleton; 사용자가 깨어난 후 채움)

---

## 진행 타임라인

`TIMELINE.md` 의 ISO 타임스탬프 audit trail 참고. 핵심 마일스톤:

- Sprint 0 — 포팅 + 5 checkpoint stub propagation (commit `f6e99b4`)
- Sprint 1 — universal writer + 4 format skill + 16 writer replay 라이브 녹화 (commit `90f2ccc`)
- Sprint 2 — scrubber 일반화 + copy-killer (LLM-free) + structure-critic 16 critic 라이브 녹화 (commit `509be40`)
- Sprint 3 — fact-checker (LLM-free) + orchestrator picker + 16 fixture full pipeline + dogfood 4 (commit `<filled at commit time>`)

각 sprint 의 `checkpoint_sprint{N}.sh PASS → 커밋 → TIMELINE DONE marker → 다음 sprint` 사이클이 깨지지 않은 채 완료. cascade fail 0건.

(사용자: 깨어난 후 본인 평가 한 줄)

## 잘된 점

(사용자가 채움. 후보:)
- TDD 우선 강제 — tests fail-first 후 구현, 후속 회귀 발견 0건
- LLM-free 파이프라인 stage 4개 (writer-replay / scrubber / copy-killer / fact-checker) 모두 결정성 byte-for-byte
- D7 replay stale cascade lock 한 번도 발동 안 함 — dispatch_key 변경 시 자동 재녹화 금지가 의도대로 작동
- D9 numeric picker — 0 LLM 호출로 4 format 진입점 분리
- bash 3.2 호환성 (associative array 회피, `{ grep || true; }` 패턴) — macOS 기본 셸 환경에서 cold-restart 가능
- D5 `.venv` FORCED + 5 checkpoint propagation block 한 번에 박힘 (challenge-2 cascade fail 4 사례에서 도출한 §9 원칙 반영)

## 문제점

(사용자가 채움. 후보:)
- Sprint 3 letter/condolence-parent 초기 critic verdict REJECT — 사용자가 fixture YAML 의 skeleton 깊이를 보강 (구체 장면 + 수신자 호명) → writer/critic 1-fixture 라이브 재녹화로 ITERATE 로 flip. D7 의 "자동 재녹화 금지" 는 silent overnight scenario 를 막기 위한 것이고, sprint-3 안에서 의도적 재녹화는 별개라는 자기-결정. TIMELINE 에 결정 기록.
- bash 3.2 + `set -euo pipefail` + `grep | wc -l` 조합에서 grep no-match (exit 1) 가 pipeline 전체 실패로 전파되어 sprint-3 checkpoint 가 silent EXIT=1 — `{ grep || true; }` 으로 격리. sprint-0 에서는 같은 패턴이 적용되어 있었으나 sprint-3 stub 전환 시 빠뜨림.
- copy-killer monotone_ending_ratio 가 한국어 ~다 prose 에서 ~0.9 typical — language structural 신호이지 AI tell 이 아님. weight 0.15 로 saturate 방지, but limitation README 에 명시 필요 (이미 sprint 2 TIMELINE 결정).
- fact-checker 의 dogfood (16 fixture 중 11개 BLOCKED) — known_facts.yml 시드가 4 항목뿐이므로 정상. 사용자 yaml 큐레이션이 dogfood 의 본질.

## 아쉬운 점

(사용자가 채움.)
- structure-critic 단일 .md 4 mode section 은 cost (opus 1 호출 / fixture) 를 4 호출 / fixture 로 분리하지 않았기 때문에 모드별 재호출이 필요할 때 재사용성이 다소 낮음. 향후 challenge 에서 mode-별 agent 분리 검토.
- copy-killer 는 외부 detector 통과 보장 X. README 에 명시된 한계지만 실제 외부 detector 결과와 비교 데이터 없음 — challenge-4 에서 비교 dataset 첨부 가치 있음.
- dogfood 4 회 모두 sonnet writer 만 호출 (critic / fact-checker 는 사용자 yaml 부족으로 BLOCKED). 사용자 yaml 큐레이션 후 재 dogfood 1 라운드 권장.

## dogfood 사용자 평가

`fixtures/dogfood/{blog,cover-letter,paper,letter}.md` 4 개 파일 평가:

| Format | 파일 | 평가 (사용자가 채움) |
|--------|------|------------------|
| blog | `fixtures/dogfood/blog.md` | (한 줄) |
| cover-letter | `fixtures/dogfood/cover-letter.md` | (한 줄) |
| paper | `fixtures/dogfood/paper.md` | (한 줄) |
| letter | `fixtures/dogfood/letter.md` | (한 줄) |

각 파일 옆에 `*.copy_killer.json` (ai_score) + `*.fact_checker.json` (yaml diff) 도 있음.

## challenge-4 에 반영할 원칙 (후보)

(사용자가 채움. 본 회고 후 `../CLAUDE.md` 또는 `../PLAYBOOK.md` 직접 수정으로 자동 전파.)

- 후보 13: bash 3.2 호환 강제 — `{ grep || true; }` 패턴, associative array 금지를 PLAYBOOK overnight skeleton 에 명시
- 후보 14: dispatch_key 변경 시 D7 stale cascade 와 의도적 fixture 보강(sprint-안-재녹화) 의 경계 명문화. `.half_scope=replay_stale` 은 silent overnight 만, sprint 안 재녹화는 TIMELINE 결정 기록으로 통과.
- 후보 15: VERIFY.sh 는 `set -e` 대신 GATES_FAILED 누적 + 마지막 일괄 판정 패턴 — 어떤 게이트가 fail 인지 한 번에 보임 (1-command 검증의 가치 보존).

## 비용

| 항목 | 호출 | 추정 |
|------|------|------|
| Sprint 1 writer (16 fixture) | 16 × sonnet | ~$1.05 |
| Sprint 2 critic (16 fixture) | 16 × opus | ~$2.72 |
| Sprint 3 fixture 보강 재녹화 | 1 writer + 1 critic | ~$0.24 |
| Sprint 3 dogfood | 4 × sonnet writer | ~$0.26 |
| **소계** | | **~$4.27** |

cost_probe.txt 정적 cap = $7.50. 실제 사용 = ~$4.27. 차이는 retry buffer + safety margin 잔여.
