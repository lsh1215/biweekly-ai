"""structure-critic single .md with 4 mode sections (M2).

The agent file `aiwriting/agents/aiwriting-structure-critic.md` must contain:
  - frontmatter: model: opus, tools: Read, Grep (no Write/Edit)
  - body sections: ## Common, ## Mode: blog, ## Mode: cover-letter,
    ## Mode: paper, ## Mode: letter
  - explicit verdict vocabulary: APPROVE / ITERATE / REJECT
  - mode-aware loader instruction (read mode param, only apply matching section)
"""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
AGENT_PATH = ROOT / "aiwriting" / "agents" / "aiwriting-structure-critic.md"


def _read():
    assert AGENT_PATH.is_file(), f"missing {AGENT_PATH}"
    return AGENT_PATH.read_text()


def test_agent_file_exists():
    content = _read()
    assert content.strip(), "structure-critic agent file is empty"


def test_frontmatter_lists_opus_model_and_read_only_tools():
    content = _read()
    fm_match = re.match(r"---\n(.*?)\n---\n", content, re.DOTALL)
    assert fm_match, "no YAML frontmatter"
    fm = fm_match.group(1)
    assert re.search(r"^model:\s*opus", fm, re.MULTILINE), "model: opus required"
    tools_match = re.search(r"^tools:\s*(.+)$", fm, re.MULTILINE)
    assert tools_match, "tools: line required"
    tools_line = tools_match.group(1)
    assert "Read" in tools_line and "Grep" in tools_line
    # disallowed tools sanity: do not grant Write/Edit. Either absent from `tools:`
    # OR explicitly listed in disallowedTools.
    if "Write" in tools_line or "Edit" in tools_line:
        # The frontmatter must explicitly disallow them elsewhere.
        assert re.search(r"^disallowedTools:\s*.*(Write|Edit)", fm, re.MULTILINE), (
            "Write/Edit listed in tools but not in disallowedTools"
        )


def test_four_mode_sections_present():
    content = _read()
    modes = re.findall(r"^## Mode:\s*(blog|cover-letter|paper|letter)\s*$",
                       content, re.MULTILINE)
    assert set(modes) == {"blog", "cover-letter", "paper", "letter"}, f"modes={modes}"


def test_common_section_present():
    content = _read()
    assert re.search(r"^## Common\s*$", content, re.MULTILINE), "## Common section missing"


def test_verdict_vocabulary_documented():
    content = _read()
    for verdict in ("APPROVE", "ITERATE", "REJECT"):
        assert verdict in content, f"{verdict} verdict missing from agent body"


def test_mode_param_loader_documented():
    content = _read()
    # The body must instruct the agent to read a `mode:` param and apply only
    # the matching section (single-md, 4-mode design).
    assert re.search(r"\bmode\s*[:=]\s*(blog|cover-letter|paper|letter)",
                     content), "mode param contract missing"
