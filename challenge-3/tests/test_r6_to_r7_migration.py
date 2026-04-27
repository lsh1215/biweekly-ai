"""Critic C3 — original blog skill said 'R1-R6'; ai-tell-rules now has R7.

After porting we MUST migrate every 'R1-R6' / 'R1–R6' to 'R1-R7'.
A stale 'R1-R6' string is a sign the port forgot to update other refs.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_SKILLS = ROOT / "aiwriting" / "skills"
PLUGIN_AGENTS = ROOT / "aiwriting" / "agents"


def _grep(pattern: str, target: Path) -> str:
    if not target.exists():
        return ""
    result = subprocess.run(
        ["grep", "-rE", pattern, str(target)],
        capture_output=True,
        text=True,
    )
    return result.stdout


def test_no_stale_r6_in_skills():
    out = _grep(r"R1.{0,3}R6\b", PLUGIN_SKILLS)
    assert out == "", f"stale R1-R6 reference in skills:\n{out}"


def test_no_stale_r6_in_agents():
    out = _grep(r"R1.{0,3}R6\b", PLUGIN_AGENTS)
    assert out == "", f"stale R1-R6 reference in agents:\n{out}"


def test_r7_exists_in_ai_tell_rules():
    rules = PLUGIN_SKILLS / "blog" / "ai-tell-rules.md"
    assert rules.exists(), f"{rules} missing"
    text = rules.read_text(encoding="utf-8")
    assert "R7" in text, "ai-tell-rules.md must mention R7"
