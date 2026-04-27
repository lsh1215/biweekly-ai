"""Critic C2 — environment propagation enforced across 5 shell files.

Sprint 0 must produce checkpoint_sprint{0,1,2,3}.sh + VERIFY.sh, all sharing
the same first 4-line propagation header so future sprints cannot drift.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    ROOT / "scripts" / "checkpoint_sprint0.sh",
    ROOT / "scripts" / "checkpoint_sprint1.sh",
    ROOT / "scripts" / "checkpoint_sprint2.sh",
    ROOT / "scripts" / "checkpoint_sprint3.sh",
    ROOT / "VERIFY.sh",
]


def test_all_5_files_exist():
    for t in TARGETS:
        assert t.exists(), f"missing: {t}"


def test_all_files_source_venv():
    for t in TARGETS:
        text = t.read_text(encoding="utf-8")
        assert "source .venv/bin/activate" in text, f"{t} missing .venv activate"


def test_all_files_have_venv_guard():
    for t in TARGETS:
        text = t.read_text(encoding="utf-8")
        assert ".venv" in text and "missing" in text.lower(), (
            f"{t} missing .venv existence guard"
        )


def test_all_files_use_strict_mode():
    for t in TARGETS:
        text = t.read_text(encoding="utf-8")
        assert "set -euo pipefail" in text, f"{t} missing strict mode"


def test_all_files_use_relative_cd():
    """CLAUDE.md §7 — cd uses $(dirname "$0").

    Grep gate strings like grep -r "/Users/leesanghun" inside the body
    are allowed (those are portability gates, not absolute-path uses).
    The real check: cd lines never hardcode a home dir.
    """
    import re
    cd_pattern = re.compile(r'^\s*cd\s+(.+)$', re.MULTILINE)
    for t in TARGETS:
        text = t.read_text(encoding="utf-8")
        cd_targets = cd_pattern.findall(text)
        assert cd_targets, f"{t} has no cd line"
        for ct in cd_targets:
            assert "/Users/" not in ct, f"{t} cd targets absolute path: {ct!r}"
        assert "$(dirname \"$0\")" in text, f"{t} must use $(dirname \"$0\") relative cd"


def test_no_docker_compose_dash():
    """CLAUDE.md §11 — no 'docker-compose' (hyphen)."""
    for t in TARGETS:
        text = t.read_text(encoding="utf-8")
        assert "docker-compose" not in text, f"{t} uses docker-compose (hyphen)"


def test_no_anthropic_api_key_hard_check():
    """CLAUDE.md §12 — no env var hard-check that exits."""
    for t in TARGETS:
        text = t.read_text(encoding="utf-8")
        # forbid pattern: ANTHROPIC_API_KEY ... exit
        # rough heuristic: no "ANTHROPIC_API_KEY" at all in checkpoints
        assert "ANTHROPIC_API_KEY" not in text, (
            f"{t} performs ANTHROPIC_API_KEY hard-check (CLAUDE.md §12)"
        )
        assert "claude -p \"ping\"" not in text and "claude -p ping" not in text, (
            f"{t} performs claude -p ping preflight (CLAUDE.md §12)"
        )
