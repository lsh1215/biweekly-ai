---
name: blog
description: Korean technical blog writing pipeline. Orchestrates a 5-stage agent pipeline (writer -> scrubber -> copy-killer -> structure-critic -> fact-checker) to produce externally publishable Korean technical blog posts with deterministic anti-AI-detection cleanup. Use when the user mentions writing a blog post, technical article, or asks to "write a blog about X". Argument "review" runs only the AI-tell scrubber on an existing file.
argument-hint: "[topic]" or "review [path]"
user-invocable: true
---

# Blog Pipeline (Orchestrator)

## Pipeline overview

```
Phase 0  Template selection           [main context, interactive]
Phase 1  Skeleton framing             [main context, interactive]
Phase 2  aiwriting-writer subagent    [fresh context, drafts to file]
Phase 3  aiwriting-scrubber subagent  [fresh context, deterministic gates]
Phase 4  aiwriting-structure-critic   [conditional: external publish only]
Phase 4b aiwriting-copy-killer        [LLM-free score, always]
Phase 4c aiwriting-fact-checker       [LLM-free pattern, always]
Phase 5  Notion publish               [main context, MCP tools, graceful skip]
```

Hard caps: critic ITERATE loop max 2 iterations, scrubber per-call max 2 internal iterations, total draft input limit 10,000 words.

Knowledge files (referenced by subagents, not loaded into orchestrator). All paths are **plugin-relative** under `${CLAUDE_PLUGIN_ROOT}/skills/blog/` (or, equivalently, `skills/blog/...` when the plugin is installed):

- `philosophy.md` - Orwell/Zinsser/Graham/Popper principles
- `style-rules.md` - plain sentences, technical terms, sentence rhythm
- `templates.md` - 3 post structure templates
- `argumentation.md` - Toulmin model, Steel Man, skeptical stance
- `ai-tell-rules.md` - R1-R7 rules, catalogs, grep gates

The orchestrator does NOT need to read these. The subagents load them in their own contexts.

---

## Phase 0: Template Selection (Interactive)

If `$ARGUMENTS` is `review [path]`: skip Phase 0/1/2, jump to Phase 3 with the given file path. The user is asking to scrub-only an existing draft.

Otherwise, present:

```
어떤 스타일로 글을 쓸까요?

| # | 템플릿                  | 설명                                                  |
|---|------------------------|------------------------------------------------------|
| 1 | Problem-Solution (PAS) | 특정 문제를 정의하고 해결하는 구조                        |
| 2 | Development Journal    | 프로젝트 경험을 시간순으로 풀어내는 구조                  |
| 3 | General Article        | 넓은 주제를 여러 소주제로 나눠 설명하는 구조              |

번호로 선택해주세요.
```

If the user provided a topic in `$ARGUMENTS`, suggest the most fitting template with a one-line reason and ask for confirmation.

## Phase 1: Skeleton Framing (Interactive)

1. Ask the user for the **core message** in one sentence - "독자가 이 글에서 한 줄만 기억한다면 무엇이어야 하나?"
2. Generate a skeleton: one line per section of the chosen template.
3. Show the skeleton to the user. Collect feedback. Iterate until user confirms.
4. Decide tone with the user: `~다` (default for technical blog) or `~습니다` (formal polite).
5. Capture the publish target: external (portfolio/Notion public) vs internal (team memo). This determines whether Phase 4 critic runs.

## Phase 2: Spawn aiwriting-writer

Invoke the aiwriting-writer subagent via the Agent tool with `format: blog`:

```
Agent({
  subagent_type: "aiwriting-writer",
  description: "Draft blog post on {topic}",
  prompt: "
    Format: blog
    Topic: {topic}
    Template: {1/2/3}
    Skeleton:
      {section 1}: {one-liner}
      {section 2}: {one-liner}
      ...
    Tone: {~다 / ~습니다}
    Output target: blog-drafts/{kebab-case-topic}.md (current working directory)

    Load knowledge from skills/blog/{philosophy,style-rules,templates,argumentation}.md
    (plugin-relative). Return the absolute path of the saved file plus a short summary.
  "
})
```

Capture the returned absolute path. Show the path and word count to the user briefly.

## Phase 3: Spawn aiwriting-scrubber

Invoke the aiwriting-scrubber subagent. **Do not include any context about how the draft was written** - pass only the file path. This preserves fresh-eyes effectiveness.

```
Agent({
  subagent_type: "aiwriting-scrubber",
  description: "Scrub AI tells from {filename}",
  prompt: "
    Draft file: {absolute_path_from_phase_2}

    Apply R1-R7 rules from skills/blog/ai-tell-rules.md (plugin-relative).
    Return the scrub report in the format specified in that file.
  "
})
```

Capture the report. If status is `BLOCKED` or `NEEDS_HUMAN_REVIEW`, surface to user and ask whether to proceed.

If `$ARGUMENTS` was `review [path]` (review-only mode), stop here. Show the scrub report and exit.

## Phase 4: Conditional - Spawn aiwriting-structure-critic

Run the critic only if **publish target = external** (decided in Phase 1).

```
Agent({
  subagent_type: "aiwriting-structure-critic",
  description: "Critique argumentation of {filename}",
  prompt: "
    Draft file: {absolute_path}
    Format: blog
    Publish target: external
    This is iteration {1 or 2} of the critic loop.

    Evaluate per skills/blog/argumentation.md (plugin-relative).
    Return verdict: APPROVE / ITERATE / REJECT with the prescribed format.
  "
})
```

### Critic loop logic (max 2 iterations)

- **APPROVE on iter 1**: proceed to Phase 4b/4c.
- **ITERATE on iter 1**: surface the improvement requests to the user. User confirms which to apply, then re-spawn aiwriting-writer with the diff request OR aiwriting-scrubber if the issues are scrubber-relevant. Re-spawn critic as iter 2.
- **APPROVE on iter 2**: proceed.
- **ITERATE on iter 2**: do NOT loop again. Surface the remaining issues to user. Ask: proceed to publish anyway / hand back for manual edits / abort.
- **REJECT** at any iter: stop the pipeline. Show the structural objection. The draft needs human re-architecting before retrying.

## Phase 4b: aiwriting-copy-killer (LLM-free)

Always runs after Phase 3 (or Phase 4 if it ran). LLM-free pure-Python score:

```
Agent({
  subagent_type: "aiwriting-copy-killer",
  description: "Score AI-likeness of {filename}",
  prompt: "Draft file: {absolute_path}. Threshold: 0.35."
})
```

Returns `PASS` or `BLOCKED` with a 6-indicator report. Surface the score to the user. The README explicitly disclaims that this score does NOT guarantee external detector pass.

## Phase 4c: aiwriting-fact-checker (LLM-free)

Always runs at the end. LLM-free pattern check against user-supplied `known_facts.yml`:

```
Agent({
  subagent_type: "aiwriting-fact-checker",
  description: "Fact-check {filename}",
  prompt: "Draft file: {absolute_path}. Known facts: known_facts.yml (cwd)."
})
```

Returns a list of unverified hard-evidence items (numbers, semver, quotes, dates, proper nouns).

## Phase 5: Notion Publish

# Phase 5 (Notion publish) - graceful skip if MCP unavailable
if Notion MCP not available:
  notice "Notion MCP not configured, draft saved locally at {absolute_path}"
  return success

If Notion MCP IS available, only proceed after explicit user confirmation:

```
> 초고가 완성되었습니다. (`{absolute_path}`)
> 1. 수정 요청 - 피드백 주시면 반영합니다 (writer 또는 scrubber 재실행)
> 2. 노션에 발행 - 블로그 DB에 바로 올립니다
> 3. 로컬 파일로 끝내기 - 현재 md 파일로 마무리합니다
```

If the user picks 2:

### 5.1 Confirm target database

Default: 노션 블로그용 DB.

```
> 어디에 발행할까요?
> 1. 노션 블로그용 DB (기본) - 이상훈 기술 블로그
> 2. 다른 DB - 검색해서 선택합니다
```

If `2`, use `notion-search` and let the user pick.

Once confirmed, fetch the schema with `notion-fetch` to get `data_source_id` and property names. Cache for the session.

### 5.2 Read Notion Markdown spec (once per session)

`ReadMcpResourceTool` on `notion://docs/enhanced-markdown-spec`. Skip if already fetched in this session.

### 5.3 Create the page

`notion-create-pages` with:
- `data_source_id` from schema
- Title from draft H1
- Status: `Draft` (default)
- Tags/Category: derive from content, ask user if ambiguous
- Date: today
- Body: converted Markdown per the spec (preserve code blocks, language tags, tables, headings)

### 5.4 Confirm

Show the created page URL. Offer: "상태를 Published로 바꾸거나, 태그를 수정하고 싶으면 말씀해주세요."

### Fallback

If the Notion MCP call fails mid-flight (auth/network): inform the user, the local draft is already saved, suggest manual copy-paste.

---

## Decision matrix - when to skip stages

| Scenario | writer | scrubber | critic | copy-killer | fact-checker | publish |
|---|---|---|---|---|---|---|
| User asks to write & publish externally | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| User asks to write internal note | ✓ | ✓ | skip | ✓ | ✓ | optional |
| User invokes `/blog review {path}` | skip | ✓ | skip | ✓ | ✓ | skip |
| User asks to argue a stance (debate prep) | ✓ | ✓ | ✓ | ✓ | ✓ | skip |

## Cost & safety guards

- Critic loop: hard cap 2 iterations, surface remaining issues to user.
- Scrubber loop: hard cap 2 internal iterations, returns `BLOCKED` if gates still red.
- Draft size: scrubber returns `INPUT_TOO_LARGE` over 10,000 words. Orchestrator must split before retry.
- Subagent isolation: never paste a previous subagent's full output as context to the next subagent. Pass only what the next stage needs (file path, decisions, not reasoning history).

## Important notes

- Do not copy book content verbatim - write in the user's internalized vocabulary.
- Do not include greetings ("Hello, today we will learn about ~").
- Do not end with filler ("Thank you", "I hope this was helpful").
- Tone is "talking with a knowledgeable colleague" - not stiff, not casual.
