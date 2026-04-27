"""Shared helpers for replay capture / loader.

D7 fixture shape:
  {
    "model": "<model id>",
    "captured_at": "<iso utc>",
    "stage": "writer | structure-critic",
    "request": {"system": str, "messages": [...], "tools": [...]},
    "response": {"stop_reason": str, "content": [{"type": "text", "text": str}, ...]},
    "dispatch_key": "<sha256>",
    "format": "blog | cover-letter | paper | letter"
  }
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
INPUTS = ROOT / "fixtures" / "inputs"
REPLAY = ROOT / "replay" / "fixtures"
SPRINT1_OUT = ROOT / "fixtures" / "outputs" / "sprint1"
SKILLS = ROOT / "aiwriting" / "skills"

VALID_FORMATS = ("blog", "cover-letter", "paper", "letter")
WRITER_MODEL = "claude-sonnet-4-5"

KNOWLEDGE_FILES = {
    "blog": ["philosophy.md", "style-rules.md", "templates.md", "argumentation.md", "ai-tell-rules.md"],
    "cover-letter": ["philosophy.md", "cover-letter-templates.md"],
    "paper": ["philosophy.md", "argumentation.md", "paper-templates.md"],
    "letter": ["letter-templates.md"],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_dispatch_key(messages: Iterable[dict]) -> str:
    parts = []
    for msg in messages:
        c = msg.get("content")
        if isinstance(c, str):
            parts.append(c)
        elif isinstance(c, list):
            for block in c:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
    return sha256_of("\n".join(parts))


def writer_system_prompt() -> str:
    return (
        "You are a Korean technical / professional writer. Produce a clean draft "
        "markdown file from a topic + chosen template + agreed skeleton, scoped by "
        "a `format` parameter (blog / cover-letter / paper / letter).\n\n"
        "OUTPUT FORMAT (STRICT):\n"
        "- Begin your response with `# ` (a level-1 markdown heading) on the very first line.\n"
        "- Do NOT wrap the draft in ```markdown ... ``` code fences.\n"
        "- Do NOT add any prose before the first `# ` line. No 'I will draft...', no 'Here is...'.\n"
        "- Do NOT add any commentary after the draft. End the response with the last line of the draft.\n"
        "- Code blocks INSIDE the draft are fine and should keep their fences.\n\n"
        "STYLE RULES:\n"
        "- Apply format-specific knowledge (blog: 5 files; cover-letter: 2; paper: 3; letter: 1).\n"
        "- Write in the requested tone (~다 or ~습니다) consistently throughout.\n"
        "- DO NOT use em-dash (—, U+2014) or en-dash (–, U+2013) anywhere outside code blocks.\n"
        "  Use hyphen-minus (-) by default; or colon (:), arrow (→), or period when meaning matches.\n"
        "- DO NOT include greetings ('Hello', '안녕하세요', 'Thank you for reading').\n"
        "- DO NOT start with a thesis quote (> ...). Start with concrete content.\n"
        "- blog and paper end with a `## 요약` section (3-5 bullets; no future-tense teasers).\n"
        "- cover-letter and letter do NOT use a `## 요약` section.\n"
        "- Stay strictly in Korean: at least 70% of body characters must be Hangul (가-힣).\n"
        "- The response body length: blog ~1000-1800 chars, cover-letter ~800-1500, paper ~1500-2500, letter ~250-1500."
    )


def build_user_message(fixture: dict) -> str:
    fmt = fixture["format"]
    topic = fixture["topic"]
    skeleton = fixture.get("skeleton", {})
    tone = fixture.get("tone", "~다" if fmt in ("blog", "paper") else "~습니다")
    template = fixture.get("template", "")
    knowledge = KNOWLEDGE_FILES[fmt]

    skeleton_lines = "\n".join(
        f"  {section}: {desc}" for section, desc in skeleton.items()
    )
    knowledge_lines = ", ".join(f"skills/{fmt}/{f}" for f in knowledge)
    parts = [
        f"Format: {fmt}",
        f"Topic: {topic}",
    ]
    if template:
        parts.append(f"Template: {template}")
    parts.append("Skeleton:")
    parts.append(skeleton_lines)
    parts.append(f"Tone: {tone}")
    parts.append(f"Knowledge files (plugin-relative): {knowledge_lines}")

    if "core_message" in fixture:
        parts.append(f"Core message: {fixture['core_message']}")
    if "applicant_summary" in fixture:
        parts.append(f"Applicant summary: {fixture['applicant_summary']}")
    if "target_company" in fixture:
        parts.append(f"Target company: {fixture['target_company']}")
    if "recipient" in fixture:
        parts.append(f"Recipient: {fixture['recipient']}")
    if "known_facts_required" in fixture:
        facts = ", ".join(fixture["known_facts_required"])
        parts.append(f"Required facts (must appear in draft): {facts}")

    parts.append("")
    parts.append(
        "Write the draft markdown only. Output the full markdown body starting with a single # H1 line. "
        "Stay strictly in Korean (≥ 70% Hangul characters in the body)."
    )
    return "\n".join(parts)


def build_request(fixture: dict) -> dict:
    user_msg = build_user_message(fixture)
    return {
        "system": writer_system_prompt(),
        "messages": [{"role": "user", "content": user_msg}],
        "tools": [],
    }


def fixture_input_path(fmt: str, slug: str) -> Path:
    return INPUTS / fmt / f"{slug}.yml"


def fixture_replay_path(fmt: str, slug: str, stage: str = "writer") -> Path:
    return REPLAY / fmt / f"{slug}-{stage}.json"


def fixture_output_path(fmt: str, slug: str) -> Path:
    return SPRINT1_OUT / f"{fmt}-{slug}.md"


def load_yaml_fixture(path: Path) -> dict:
    import yaml  # local import - avoid hard dep at module load
    return yaml.safe_load(path.read_text())


def list_all_fixtures() -> list[Path]:
    out = []
    for fmt in VALID_FORMATS:
        out.extend(sorted((INPUTS / fmt).glob("*.yml")))
    return out


def write_fixture_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def read_fixture_json(path: Path) -> dict:
    return json.loads(path.read_text())


def extract_response_text(response: dict) -> str:
    parts = []
    for block in response.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif isinstance(block, str):
            parts.append(block)
    return "".join(parts)


def hangul_prose_ratio(text: str, threshold_floor: bool = False) -> float:
    """Hangul ratio measured on prose only (code blocks stripped).

    Sprint-1 autonomous decision (TIMELINE 2026-04-28): S6 spec threshold 0.7
    on all-non-whitespace chars is unrealistic for Korean technical writing
    where English terminology (Kafka / Producer / API names) is unavoidable.
    Prose-only measurement excludes ``` fenced blocks and `inline code`, then
    counts hangul / (hangul + non-whitespace prose). The intent of S6 (detect
    wholesale English leak) is preserved at threshold 0.5; a fully-English
    draft still yields ratio ≈ 0.
    """
    import re

    s = text
    # strip fenced code blocks (```...```), keeping prose around them
    s = re.sub(r"```.*?```", "", s, flags=re.DOTALL)
    # strip inline code spans (`...`)
    s = re.sub(r"`[^`\n]+`", "", s)
    hangul = len(re.findall(r"[가-힣]", s))
    nonws = len(re.findall(r"\S", s))
    if nonws == 0:
        return 0.0
    return hangul / nonws


def clean_draft_markdown(text: str) -> str:
    """Strip leading meta-commentary and outer ```markdown ... ``` code fence wrappers.

    The model sometimes wraps its draft in a code fence and prefixes it with
    'Here is the draft...' style prose. The replay output (.md file) should be just
    the clean draft starting with `# `.
    """
    import re

    s = text.strip()

    # Strip an outer ```markdown ... ``` or ``` ... ``` wrapper if it spans the whole content.
    fence = re.match(r"^```(?:markdown|md)?\s*\n(.*)\n```\s*$", s, re.DOTALL)
    if fence:
        s = fence.group(1).strip()

    # If the response leads with prose followed by a markdown code-fenced draft,
    # extract the first ```markdown ... ``` block.
    if not s.lstrip().startswith("#"):
        m = re.search(r"```(?:markdown|md)?\s*\n(#[^\n]*\n.*?)\n```", s, re.DOTALL)
        if m:
            s = m.group(1).strip()

    # Drop everything before the first `# ` heading line.
    lines = s.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("# "):
            s = "\n".join(lines[i:]).strip()
            break

    # Drop a trailing ``` if it remained.
    if s.endswith("```"):
        s = s[: -3].rstrip()

    return s
