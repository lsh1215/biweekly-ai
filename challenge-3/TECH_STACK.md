# challenge-3 TECH_STACK

## Plugin format
- **Claude Code plugin spec** — `.claude-plugin/plugin.json` metadata-only 4 필드 (name/version/description/author).
- **Discovery 컨벤션** — `agents/*.md`, `skills/<name>/SKILL.md`, `.mcp.json`, `hooks/`. plugin.json에 명시 X.
- **marketplace.json** — `source: "./"` (local). schema URL: `https://anthropic.com/claude-code/marketplace.schema.json`.

## Language / Runtime
- **Python 3.13** (system default)
- **`.venv`** — challenge-3/.venv (D5 forced)

## 의존성
- `pytest` — TDD 강제 (CLAUDE.md §2)
- `pyyaml` — manifest/fixture YAML 파싱
- `regex` (PyPI) — 한글 음절 카운트 (stdlib re 한글 정밀도 부족)
- `jsonschema` — plugin.json/marketplace.json schema validate fallback (S1)

`requirements.txt`:
```
pytest>=8.0
pyyaml>=6.0
regex>=2024.11.6
jsonschema>=4.0
```

## Models
| Stage | Model | 비용 (per 1M) |
|-------|-------|--------------|
| writer | claude-sonnet-4-5 | $3 in / $15 out |
| scrubber | claude-sonnet-4-5 | $3 in / $15 out |
| copy-killer | (Python, 없음) | $0 |
| fact-checker | (Python, 없음) | $0 |
| structure-critic | claude-opus-4-7 | $15 in / $75 out |

총 cap: $7.50 (PRD §8 정적 추정)

## CLI
- `claude` (Claude Code) — Sprint 1 라이브 녹화 + dogfood만 사용
- `python3 -m venv` (system default Python 3.13)

## OS / 머신
- macOS 14+ (Darwin 23.6.0 검증)
- `caffeinate -di` — 슬립 방지 필수 (CLAUDE.md 리밋 대응)

## 테스트 전략
- **Unit (pytest)** 11+ — LLM-free deterministic
- **Integration** 4 — replay-driven E2E
- **Replay 단위** — structure-critic 16 verdict 결정성
- **VERIFY.sh** — 10 gate 1-command
- **dogfood 4회** — 사용자 검증 (Sprint 3 마지막 또는 기상 후)
