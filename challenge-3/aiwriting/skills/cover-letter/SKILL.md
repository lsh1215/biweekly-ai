---
name: cover-letter
description: Korean cover-letter writing pipeline. Drafts an applicant cover letter (자기소개서) in STAR (Situation/Task/Action/Result) form, then runs deterministic AI-tell scrubbing. Use when the user asks for a cover letter, 자기소개서, or career transition statement. Argument "review" runs only the AI-tell scrubber on an existing file.
argument-hint: "[role @ company]" or "review [path]"
user-invocable: true
---

# Cover-letter Pipeline (Orchestrator)

## Pipeline overview

```
Phase 0  Inputs collection            [main context, interactive]
Phase 1  Skeleton framing             [main context, interactive]
Phase 2  aiwriting-writer subagent    [fresh context, drafts to file]
Phase 3  aiwriting-scrubber subagent  [fresh context, R1-R7 deterministic]
Phase 4b aiwriting-copy-killer        [LLM-free score, always]
Phase 4c aiwriting-fact-checker       [LLM-free pattern, always]
```

The structure-critic (Phase 4) is **not** routed for cover-letter by default. The argumentation rigor demanded for blog/paper exceeds what hiring readers expect; STAR clarity matters more.

Knowledge files (loaded by subagents, not orchestrator), under `${CLAUDE_PLUGIN_ROOT}/skills/cover-letter/`:

- `philosophy.md` - shared with blog/paper (Orwell/Zinsser/Graham/Popper)
- `cover-letter-templates.md` - STAR template + opening hook patterns + closing patterns

The orchestrator does NOT load these.

---

## Phase 0: Inputs (Interactive)

If `$ARGUMENTS` is `review [path]`, jump to Phase 3 (scrub-only) on the given file.

Otherwise, collect:

- 지원 회사 / 직무 / 연차
- 한 줄로 본인의 강점 (왜 합격해야 하는가)
- 가장 단단한 사례 1-2개 (수치 가능하면 수치)
- 톤: `~습니다` (default for cover-letter) or `~다`

If the user pasted a job description, skim and ask:
> 지원 동기를 회사 측 어떤 한 줄(JD 발췌)에 묶을까요?

## Phase 1: Skeleton Framing (Interactive)

1. Generate a 5-section skeleton: intro / experience1 / experience2 / fit / closing.
2. Each line is the topic sentence the section will defend (STAR shape). Show to user, iterate until confirmed.
3. Confirm tone. Default `~습니다`.

## Phase 2: Spawn aiwriting-writer

```
Agent({
  subagent_type: "aiwriting-writer",
  description: "Draft cover-letter for {role} @ {company}",
  prompt: "
    Format: cover-letter
    Topic: {role} @ {company}
    Skeleton:
      intro: {one-liner}
      experience1: {one-liner}
      experience2: {one-liner}
      fit: {one-liner}
      closing: {one-liner}
    Tone: {~습니다 / ~다}
    Output target: cover-letter-drafts/{kebab-case-slug}.md (current working directory)

    Load knowledge from skills/cover-letter/{philosophy,cover-letter-templates}.md
    (plugin-relative). Return the absolute path of the saved file plus a short summary.
  "
})
```

Capture the returned absolute path.

## Phase 3: Spawn aiwriting-scrubber

```
Agent({
  subagent_type: "aiwriting-scrubber",
  description: "Scrub AI tells from {filename}",
  prompt: "
    Draft file: {absolute_path_from_phase_2}
    Format: cover-letter

    Apply R1-R7 from skills/blog/ai-tell-rules.md (plugin-relative).
    Cover-letter does NOT require a `## 요약` section - skip the R3 summary insertion.
    Return the scrub report.
  "
})
```

If `$ARGUMENTS` was `review [path]`, stop here and surface the report.

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

Hard-evidence categories (numbers, dates, semver, quotes, proper nouns) are flagged when not in `known_facts.yml`. For cover-letter, this catches inflated experience claims and unverified company facts.

## Decision matrix

| Scenario | writer | scrubber | critic | copy-killer | fact-checker |
|---|---|---|---|---|---|
| Standard cover-letter | yes | yes | skip | yes | yes |
| `/aiwriting:cover-letter review {path}` | skip | yes | skip | yes | yes |
| User insists on argumentation review | yes | yes | optional | yes | yes |

## Important notes

- 자기소개서 첫 문장은 가장 단단한 단언으로. "안녕하세요" 류 인사 금지.
- "최선을 다하겠습니다" 류 추상 수식어 0회 (R2 + ai-tell-rules.md 카탈로그).
- 회사명·직무명은 본문 어딘가 1회는 명시.
- 수치는 known_facts.yml 의 항목으로 yaml 등록. fact-checker 가 통과시킨다.
