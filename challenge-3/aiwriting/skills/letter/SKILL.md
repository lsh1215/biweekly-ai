---
name: letter
description: Korean personal letter writing pipeline (감사/축하/위로/추천 등). Drafts a personal letter focused on warmth and specificity over structure, then runs deterministic AI-tell scrubbing. Use when the user asks for a personal letter, 감사 편지, 위로 편지, 축하 메시지, 또는 추천서. Argument "review" runs only the AI-tell scrubber on an existing file.
argument-hint: "[letter purpose]" or "review [path]"
user-invocable: true
---

# Letter Pipeline (Orchestrator)

## Pipeline overview

```
Phase 0  Inputs collection            [main context, interactive]
Phase 1  Skeleton framing             [main context, interactive]
Phase 2  aiwriting-writer subagent    [fresh context, drafts to file]
Phase 3  aiwriting-scrubber subagent  [fresh context, R1-R7 deterministic]
Phase 4b aiwriting-copy-killer        [LLM-free score, always]
Phase 4c aiwriting-fact-checker       [LLM-free pattern, always]
```

structure-critic (Phase 4) 는 letter 에서 **skip**. 논증 강도가 본질이 아니라 **구체적 한 장면 + 따뜻함** 이 본질. 논증 critic 은 letter 에서 false positive 를 양산한다.

Knowledge files (loaded by subagents), under `${CLAUDE_PLUGIN_ROOT}/skills/letter/`:

- `letter-templates.md` - 4 letter type templates (감사 / 축하 / 위로 / 추천) + 톤 가이드

The orchestrator does NOT load this.

---

## Phase 0: Inputs (Interactive)

If `$ARGUMENTS` is `review [path]`, jump to Phase 3 (scrub-only).

Otherwise, collect:

- letter type (감사 / 축하 / 위로 / 추천 / 기타)
- 수신자 (관계 + 친밀도 + 직함 가능 시)
- 핵심 메시지 한 줄 (전달하고 싶은 한 가지)
- 톤: `~습니다` (default for 격식 letter) or `~다` (peer 편지)

## Phase 1: Skeleton Framing (Interactive)

Generate a short skeleton:

- 감사/축하/위로: opening / body1 / (body2) / closing (3-4 섹션)
- 추천서: opening / body1 / body2 / body3 / closing (4-5 섹션, 더 형식적)

본 단계에서 **구체적 한 장면** 을 user 가 제시할 수 있게 유도:
> 받는 사람의 어떤 한 순간 / 한 장면을 짚어 쓸까요?

## Phase 2: Spawn aiwriting-writer

```
Agent({
  subagent_type: "aiwriting-writer",
  description: "Draft letter for {recipient}",
  prompt: "
    Format: letter
    Topic: {letter type}
    Skeleton:
      opening: {one-liner}
      body1: {one-liner}
      body2 (optional): {one-liner}
      closing: {one-liner}
    Tone: {~습니다 / ~다}
    Output target: letter-drafts/{kebab-case-slug}.md (current working directory)

    Load knowledge from skills/letter/letter-templates.md (plugin-relative).
    Return the absolute path of the saved file plus a short summary.
  "
})
```

## Phase 3: Spawn aiwriting-scrubber

```
Agent({
  subagent_type: "aiwriting-scrubber",
  description: "Scrub AI tells from {filename}",
  prompt: "
    Draft file: {absolute_path}
    Format: letter

    Apply R1-R7 from skills/blog/ai-tell-rules.md (plugin-relative).
    Letter does NOT require `## 요약` - skip the R3 summary insertion.
    Letter has more freedom for sentence-rhythm warnings (heuristic only, not BLOCK).
    Return the scrub report.
  "
})
```

If `review` mode, stop here.

## Phase 4b: aiwriting-copy-killer (LLM-free)

```
Agent({
  subagent_type: "aiwriting-copy-killer",
  description: "Score AI-likeness of {filename}",
  prompt: "Draft file: {absolute_path}. Threshold: 0.35."
})
```

Letter 의 copy-killer threshold 는 default 0.35 와 동일. 다만 letter 는 connector 빈도가 더 자연스럽게 낮아져 score 가 일반적으로 더 낮게 나온다.

## Phase 4c: aiwriting-fact-checker (LLM-free)

```
Agent({
  subagent_type: "aiwriting-fact-checker",
  description: "Fact-check {filename}",
  prompt: "Draft file: {absolute_path}. Known facts: known_facts.yml (cwd)."
})
```

Letter 에서 hard-evidence 는 적다 (대부분 정성적). 그래도 수치 (예: "9개월간 함께 일했습니다") 와 고유명사 (이름, 회사명) 는 known_facts.yml 의 등록 항목과 대조한다.

## Decision matrix

| Scenario | writer | scrubber | critic | copy-killer | fact-checker |
|---|---|---|---|---|---|
| Personal letter | yes | yes | skip | yes | yes |
| `/aiwriting:letter review {path}` | skip | yes | skip | yes | yes |

## Important notes

- Letter 는 짧은 게 미덕. 200-600자가 일반적.
- "삼가 고인의 명복을 빕니다" 같은 정형구는 위로 letter 한정 1회 OK.
- 감정 형용사 ("정말 감사합니다", "너무 슬픕니다") 는 1회 이내. 구체 사건이 감정을 대신해야 한다.
- 받는 사람을 한 번도 명시하지 않은 letter 는 letter 가 아님. 1회 이상 호명.
- 추천서는 강점/약점/적합성 3 축이 모두 있어야 신뢰받는다 (intellectual honesty).
