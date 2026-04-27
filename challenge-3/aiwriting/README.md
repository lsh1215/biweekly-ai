# aiwriting

Korean multi-format writing pipeline as a Claude Code plugin. 4 formats (blog, cover-letter, paper, letter), 5 stages (writer -> scrubber -> copy-killer -> structure-critic -> fact-checker).

## Install

Add this directory to a marketplace, then:

```
/plugin marketplace add <path-to-marketplace>
/plugin install aiwriting
```

Then invoke a format directly:

```
/aiwriting:blog
/aiwriting:cover-letter
/aiwriting:paper
/aiwriting:letter
```

Or run the orchestrator and pick a number:

```
/aiwriting
```

## Pipeline

```
writer  -->  scrubber  -->  copy-killer  -->  structure-critic  -->  fact-checker
 (LLM)        (LLM)         (Pure Python)        (LLM)              (Pure Python)
```

3 stages out of 5 are deterministic Python (scrubber grep gate, copy-killer score, fact-checker pattern). 2 LLM stages are replay-driven from captured fixtures.

## Limits and honest caveats

- The copy-killer is a 6-indicator score that the plugin computes locally. It does NOT call any external AI detector. The score is a useful internal signal but does NOT guarantee that an externally-run detector (GPTZero, Originality.ai, copy-killer.com etc.) will mark the text as human. Treat the copy-killer score as a smoke test, not a certificate.
- The fact-checker covers 5 hard-evidence types (numbers, semver, direct quotes, dates, proper nouns) using regex against a user-supplied `known_facts.yml`. It does not cross-check against the open web; if your post claims something that is not in your `known_facts.yml`, the fact-checker will warn but cannot prove or disprove it.
- All knowledge files are Korean-only. English drafts will work mechanically but the style rules and AI-tell catalog will not apply.
- The structure-critic verdicts (`APPROVE` / `ITERATE` / `REJECT`) are LLM judgments and replay-driven. They are deterministic with respect to a captured fixture, not a ground truth on writing quality.

## Knowledge files

The plugin loads its writing knowledge from `skills/blog/`, `skills/cover-letter/`, `skills/paper/`, `skills/letter/` (plugin-relative paths). The asymmetry is intentional: blog has 5 knowledge files because the user has invested most heavily in blog, while letter has 1.

## License

MIT. See LICENSE.
