"""Critic C3 — no absolute paths leaked into the plugin.

After Sprint 0 port, no file under aiwriting/ may contain
'/Users/leesanghun' or other absolute home-dir references.
The plugin must be portable to any user / machine.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "aiwriting"


def test_no_absolute_user_path_in_plugin():
    assert PLUGIN.exists(), f"aiwriting/ not built yet: {PLUGIN}"
    result = subprocess.run(
        ["grep", "-r", "/Users/leesanghun", str(PLUGIN)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        f"absolute path leaked into plugin:\n{result.stdout}"
    )
    assert result.stdout == "", f"unexpected stdout: {result.stdout!r}"


def test_no_home_tilde_path_in_plugin_skills():
    """~/.claude/ references in agents/skills should be rewritten too."""
    for sub in ("agents", "skills"):
        target = PLUGIN / sub
        if not target.exists():
            continue
        result = subprocess.run(
            ["grep", "-rE", r"~/\.claude/", str(target)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, (
            f"~/.claude path leaked into {sub}/:\n{result.stdout}"
        )
