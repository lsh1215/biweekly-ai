"""D4 — blog SKILL.md Phase 5 must graceful-skip when Notion MCP unavailable.

The first guard inside Phase 5 must mention both 'Notion MCP' (or similar)
and a saved-locally fallback. Without this guard the original blog flow
breaks on machines with no Notion MCP.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "aiwriting" / "skills" / "blog" / "SKILL.md"


def test_blog_skill_exists():
    assert SKILL.exists(), f"{SKILL} missing"


def test_phase5_section_present():
    text = SKILL.read_text(encoding="utf-8")
    assert "Phase 5" in text, "SKILL.md must keep Phase 5 section"


def test_phase5_graceful_skip_guard_present():
    text = SKILL.read_text(encoding="utf-8")
    # locate Phase 5 section
    idx = text.find("Phase 5")
    assert idx >= 0
    phase5_text = text[idx:]
    # the guard must mention notion mcp + saved-locally fallback
    assert "Notion MCP" in phase5_text or "notion mcp" in phase5_text.lower()
    assert "saved locally" in phase5_text.lower() or "saved_locally" in phase5_text.lower() \
        or "로컬" in phase5_text, (
            "Phase 5 must contain a graceful-skip notice referencing local save"
        )
    # an explicit "skip" or "graceful" hint near the top
    head = phase5_text.split("\n", 8)[:8]
    head_blob = "\n".join(head).lower()
    assert "graceful" in head_blob or "skip" in head_blob or "unavailable" in head_blob, (
        f"first lines of Phase 5 must signal the guard:\n{head_blob}"
    )
