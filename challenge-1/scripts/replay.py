"""Replay system — load and display execution timeline from JSONL logs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_log(path: str) -> list[dict[str, Any]]:
    """Load entries from a JSONL log file.

    Args:
        path: Path to the JSONL log file.

    Returns:
        List of log entry dicts.
    """
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def format_timeline(entries: list[dict[str, Any]]) -> list[str]:
    """Format log entries as a human-readable timeline.

    Args:
        entries: List of log entry dicts.

    Returns:
        List of formatted timeline strings.
    """
    if not entries:
        return []

    base_time = entries[0].get("timestamp", 0)
    lines = []

    for entry in entries:
        elapsed = entry.get("timestamp", 0) - base_time
        level = entry.get("level", "INFO")
        component = entry.get("component", "?")
        event = entry.get("event", "")
        data = entry.get("data")

        line = f"[{elapsed:7.2f}s] [{level:7s}] {component:12s} | {event}"
        if data:
            data_str = json.dumps(data, default=str)
            if len(data_str) > 80:
                data_str = data_str[:77] + "..."
            line += f"  {data_str}"
        lines.append(line)

    return lines


def replay(path: str) -> None:
    """Replay a log file to stdout."""
    entries = load_log(path)
    lines = format_timeline(entries)

    print(f"=== Replay: {path} ({len(entries)} entries) ===\n")
    for line in lines:
        print(line)
    print(f"\n=== End of replay ===")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.replay <logfile.jsonl>")
        sys.exit(1)
    replay(sys.argv[1])
