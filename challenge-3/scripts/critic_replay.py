"""structure-critic replay loader (Sprint 2).

D7 7-key shape, dispatch_key = sha256 of concatenated message text.

Each critic call is built from:
  - the format/mode (blog | cover-letter | paper | letter)
  - the writer-stage draft (sprint1 output) for that fixture
  - the structure-critic system prompt (mode-specific)

Inputs:
  - replay/fixtures/{fmt}/{slug}-critic.json  (D7 shape)
Outputs (in-memory):
  - parse_verdict(text) -> "APPROVE" | "ITERATE" | "REJECT"
  - replay_all_verdicts() -> {(fmt, slug): verdict}
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import replay_common as rc

CRITIC_MODEL = "claude-opus-4-5"
CRITIC_STAGE = "structure-critic"

VERDICT_RE = re.compile(r"\b(APPROVE|ITERATE|REJECT)\b")


def critic_system_prompt(mode: str) -> str:
    base = (
        "You are an independent reviewer (aiwriting-structure-critic, model=opus). "
        "You evaluate one Korean writing draft, in one mode, in a single pass. "
        "Verdict vocabulary: APPROVE | ITERATE | REJECT (uppercase, exact). "
        "Output the verdict block under 400 words.\n\n"
        "OUTPUT (STRICT):\n"
        "## structure-critic 결과\n"
        "- mode: {mode}\n"
        "- verdict: APPROVE | ITERATE | REJECT\n"
        "- rationale: 1-3 sentences\n"
        "- action items (ITERATE only): numbered list\n\n"
        f"Mode for this call: {mode}.\n"
    )
    return base


def critic_user_message(mode: str, draft_text: str, slug: str) -> str:
    return (
        f"mode: {mode}\n"
        f"slug: {slug}\n"
        f"draft begins ↓↓↓\n{draft_text}\n↑↑↑ draft ends\n"
        "Apply only the matching ## Mode: section plus ## Common from "
        "aiwriting-structure-critic.md. Return the verdict block."
    )


def build_critic_request(fmt: str, slug: str, draft_text: str) -> dict:
    mode = fmt
    return {
        "system": critic_system_prompt(mode),
        "messages": [
            {"role": "user", "content": critic_user_message(mode, draft_text, slug)},
        ],
        "tools": [],
    }


def expected_dispatch_key(fmt: str, slug: str) -> str:
    """Recompute dispatch_key from the current sprint1 draft for fixture (fmt, slug)."""
    draft_path = rc.SPRINT1_OUT / f"{fmt}-{slug}.md"
    if not draft_path.is_file():
        raise FileNotFoundError(draft_path)
    draft_text = draft_path.read_text()
    request = build_critic_request(fmt, slug, draft_text)
    return rc.compute_dispatch_key(request["messages"])


def parse_verdict(text: str) -> str:
    """Pick the verdict token from a critic response.

    Strategy: prefer a `verdict:` line; otherwise first APPROVE/ITERATE/REJECT
    found in the body. Returns "ITERATE" as a safe fallback only if none found
    (this should not happen on a well-formed response).
    """
    m = re.search(r"verdict[^A-Za-z]*\s*:?\s*(APPROVE|ITERATE|REJECT)\b", text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    m = VERDICT_RE.search(text)
    if m:
        return m.group(1).upper()
    return "ITERATE"


def critic_replay_path(fmt: str, slug: str) -> Path:
    return rc.REPLAY / fmt / f"{slug}-critic.json"


def all_critic_replays() -> list[Path]:
    out = []
    for fmt in rc.VALID_FORMATS:
        out.extend(sorted((rc.REPLAY / fmt).glob("*-critic.json")))
    return out


def load_critic_text(path: Path) -> str:
    d = json.loads(path.read_text())
    return rc.extract_response_text(d["response"])


def replay_all_verdicts() -> dict[tuple[str, str], str]:
    """Read all 16 critic replays and return parsed verdicts in deterministic order."""
    out: dict[tuple[str, str], str] = {}
    for fmt in rc.VALID_FORMATS:
        for f in sorted((rc.REPLAY / fmt).glob("*-critic.json")):
            slug = f.stem.replace("-critic", "")
            text = load_critic_text(f)
            out[(fmt, slug)] = parse_verdict(text)
    return out
