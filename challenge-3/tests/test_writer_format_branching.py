"""D1 universal writer — format param maps to format-specific knowledge file set.

  blog        : 5 (philosophy/style-rules/templates/argumentation/ai-tell-rules)
  cover-letter: 2 (philosophy/cover-letter-templates)
  paper       : 3 (philosophy/argumentation/paper-templates)
  letter      : 1 (letter-templates)
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
WRITER = ROOT / "aiwriting" / "agents" / "aiwriting-writer.md"
SKILLS = ROOT / "aiwriting" / "skills"

EXPECTED_FILES = {
    "blog": [
        "philosophy.md",
        "style-rules.md",
        "templates.md",
        "argumentation.md",
        "ai-tell-rules.md",
    ],
    "cover-letter": ["philosophy.md", "cover-letter-templates.md"],
    "paper": ["philosophy.md", "argumentation.md", "paper-templates.md"],
    "letter": ["letter-templates.md"],
}


def test_writer_agent_file_exists():
    assert WRITER.is_file(), f"writer agent not found at {WRITER}"


def test_writer_body_under_200_lines():
    body = WRITER.read_text().splitlines()
    assert len(body) <= 200, f"writer body {len(body)} > 200 lines (D1 budget)"


def test_writer_mentions_format_param():
    content = WRITER.read_text()
    assert re.search(r"format[ _-]?param", content, re.IGNORECASE) or "format" in content
    for fmt in EXPECTED_FILES:
        assert fmt in content, f"writer missing format mention: {fmt}"


def test_writer_lists_each_format_knowledge_file_set():
    content = WRITER.read_text()
    for fmt, files in EXPECTED_FILES.items():
        for fname in files:
            stem = fname.replace(".md", "")
            assert stem in content, (
                f"writer agent does not reference '{stem}' for format '{fmt}'"
            )


def test_each_format_skill_dir_has_expected_files():
    for fmt, files in EXPECTED_FILES.items():
        skill_dir = SKILLS / fmt
        assert skill_dir.is_dir(), f"missing skill dir: {skill_dir}"
        skill_md = skill_dir / "SKILL.md"
        assert skill_md.is_file(), f"missing SKILL.md in {skill_dir}"
        for f in files:
            assert (skill_dir / f).is_file(), f"format {fmt}: missing knowledge file {f}"


def test_each_format_skill_is_user_invocable():
    for fmt in EXPECTED_FILES:
        skill_md = SKILLS / fmt / "SKILL.md"
        front = skill_md.read_text()
        assert "user-invocable: true" in front, f"{fmt}/SKILL.md missing 'user-invocable: true'"
