---
name: paper
description: Korean academic paper / technical report writing pipeline. Drafts a structured paper (Abstract / Introduction / Method / Results / Discussion / Limitations / Conclusion) with Toulmin argumentation, then runs deterministic AI-tell scrubbing and structure-critic review. Use when the user asks for a paper, technical report, 논문 초안, or empirical study writeup. Argument "review" runs only the AI-tell scrubber on an existing file.
argument-hint: "[paper topic]" or "review [path]"
user-invocable: true
---

# Paper Pipeline (Orchestrator)

## Pipeline overview

```
Phase 0  Inputs collection            [main context, interactive]
Phase 1  Skeleton framing             [main context, interactive]
Phase 2  aiwriting-writer subagent    [fresh context, drafts to file]
Phase 3  aiwriting-scrubber subagent  [fresh context, R1-R7 deterministic]
Phase 4  aiwriting-structure-critic   [argumentation review, mandatory for paper]
Phase 4b aiwriting-copy-killer        [LLM-free score, always]
Phase 4c aiwriting-fact-checker       [LLM-free pattern, always]
```

paper 포맷은 structure-critic 가 **mandatory** (blog 의 external publish 와 동급). 논문/리포트는 논증 강도가 본질이라 critic 단계를 건너뛰지 않는다.

Knowledge files (loaded by subagents), under `${CLAUDE_PLUGIN_ROOT}/skills/paper/`:

- `philosophy.md` - shared with blog/cover-letter (Orwell/Zinsser/Graham/Popper)
- `argumentation.md` - shared with blog (Toulmin / Steel Man / Skeptical stance)
- `paper-templates.md` - 7-section paper structure + abstract pattern + limitations pattern

The orchestrator does NOT load these.

---

## Phase 0: Inputs (Interactive)

If `$ARGUMENTS` is `review [path]`, jump to Phase 3 (scrub-only).

Otherwise, collect:

- 논문 주제 한 줄
- 핵심 발견 (Result 한 줄)
- 데이터셋 / 모델 / 측정 방법
- 톤: `~다` (default for paper) or `~습니다`

## Phase 1: Skeleton Framing (Interactive)

Generate a 7-section skeleton (Abstract / Introduction / Method / Results / Discussion / Limitations / Conclusion). One topic sentence per section. Iterate with user until confirmed.

Limitations 섹션은 paper 에서 **mandatory** (intellectual honesty의 핵심).

## Phase 2: Spawn aiwriting-writer

```
Agent({
  subagent_type: "aiwriting-writer",
  description: "Draft paper on {topic}",
  prompt: "
    Format: paper
    Topic: {topic}
    Skeleton:
      Abstract: {one-liner}
      Introduction: {one-liner}
      Method: {one-liner}
      Results: {one-liner}
      Discussion: {one-liner}
      Limitations: {one-liner}
      Conclusion: {one-liner}
    Tone: {~다 / ~습니다}
    Output target: paper-drafts/{kebab-case-slug}.md (current working directory)

    Load knowledge from skills/paper/{philosophy,argumentation,paper-templates}.md
    (plugin-relative). Return the absolute path of the saved file plus a short summary.
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
    Format: paper

    Apply R1-R7 from skills/blog/ai-tell-rules.md (plugin-relative).
    Paper requires `## 요약` (or Conclusion functioning as 요약). Insert if missing per R3.
    Return the scrub report.
  "
})
```

If `review` mode, stop here.

## Phase 4: Spawn aiwriting-structure-critic (mandatory)

```
Agent({
  subagent_type: "aiwriting-structure-critic",
  description: "Critique paper argumentation",
  prompt: "
    Draft file: {absolute_path}
    Format: paper
    Publish target: external (paper is always external-grade)
    This is iteration {1 or 2} of the critic loop.

    Evaluate per skills/paper/argumentation.md (plugin-relative).
    Pay special attention to:
      - Method reproducibility (수치 + dataset + 환경 명시?)
      - Results claim vs evidence gap
      - Limitations section honesty (overstated robustness?)
    Return verdict: APPROVE / ITERATE / REJECT with prescribed format.
  "
})
```

### Critic loop logic (max 2 iterations)

Same as blog: APPROVE → proceed; ITERATE → re-spawn writer with diff request, re-spawn critic; REJECT → stop and surface structural objection.

## Phase 4b: aiwriting-copy-killer (LLM-free)

```
Agent({
  subagent_type: "aiwriting-copy-killer",
  description: "Score AI-likeness of {filename}",
  prompt: "Draft file: {absolute_path}. Threshold: 0.35."
})
```

## Phase 4c: aiwriting-fact-checker (LLM-free)

```
Agent({
  subagent_type: "aiwriting-fact-checker",
  description: "Fact-check {filename}",
  prompt: "Draft file: {absolute_path}. Known facts: known_facts.yml (cwd)."
})
```

Paper 의 fact-checker 출력은 numbers/semver/dates 를 가장 엄격하게 다룬다. 모든 수치 결과는 known_facts.yml 에 등록되어 있어야 BLOCK 회피.

## Decision matrix

| Scenario | writer | scrubber | critic | copy-killer | fact-checker |
|---|---|---|---|---|---|
| Paper draft | yes | yes | yes | yes | yes |
| `/aiwriting:paper review {path}` | skip | yes | skip | yes | yes |

## Important notes

- Abstract 는 250-400자. 긴 abstract 는 reviewer 가 안 읽는다.
- Method 는 "타인이 재현 가능한가" 가 단일 기준. 재현 불가능한 한 줄은 cut.
- Limitations 는 reviewer 가 가장 먼저 본다. 약점을 명시한 paper 가 더 신뢰받는다 (Popper).
- 영어 약어는 첫 등장 시 풀이 1회.
- 한국어 paper 의 톤은 `~다` 가 일반적. journal 별 가이드 확인 권고.
