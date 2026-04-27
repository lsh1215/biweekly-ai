---
name: aiwriting
description: Korean writing pipeline orchestrator. Numeric picker that routes to one of 4 direct format slash commands (blog / cover-letter / paper / letter). Zero AI dispatch - the user picks by number. Use when the user invokes /aiwriting without specifying a format, or asks "글 쓰는 도구 뭐 있어?" / "aiwriting 메뉴" / "어떤 글을 쓸 수 있어?".
argument-hint: "" (no arguments - menu only)
user-invocable: true
---

# aiwriting Orchestrator (Numeric Picker)

This skill is a **menu only**. It does not dispatch via AI. Print the picker and wait for the user's number.

## Behavior

When invoked, print exactly:

```
어떤 글을 쓸까요?

1. blog          - 한국어 기술 블로그 (5 stage pipeline + structure-critic)
2. cover-letter  - 자기소개서 (STAR + 한국 채용 시장 관습)
3. paper         - 학술 논문 / 기술 리포트 (7 sections + Toulmin)
4. letter        - 개인 편지 (감사/축하/위로/추천)

번호 입력 → 해당 직접 슬래시로 redirect.
```

Then wait for the user's input.

## Routing rules

- `1` → instruct user to invoke `/aiwriting:blog [topic]` (or pass topic if user already provided one)
- `2` → instruct user to invoke `/aiwriting:cover-letter [role @ company]`
- `3` → instruct user to invoke `/aiwriting:paper [paper topic]`
- `4` → instruct user to invoke `/aiwriting:letter [letter purpose]`
- any other input → re-print the menu, no LLM dispatch

## Why no AI dispatch (D9)

- Cost: routing decision is trivial; no need to spend tokens.
- Determinism: numeric input → one branch. No surprise.
- Transparency: user sees the 4 options, no hidden routing.
- The 4 direct slashes (`/aiwriting:blog`, etc.) are also `user-invocable: true`. Skip this orchestrator entirely if the user already knows which format they want.

## Notes

- Do NOT call any subagent from this skill.
- Do NOT load knowledge files. The downstream skills do.
- Do NOT prompt for topic here. The downstream skill's Phase 0 collects inputs.
- This skill terminates after printing the redirect instruction. The user re-invokes the chosen direct slash.
