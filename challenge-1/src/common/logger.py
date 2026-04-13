"""Structured logging for Warehouse Picker VLA."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class LogEntry:
    """A single structured log entry."""

    timestamp: float
    level: str
    component: str
    event: str
    data: dict[str, Any] | None = None


class StructuredLogger:
    """JSONL structured logger."""

    def __init__(self, log_path: Path | str | None = None):
        self.log_path = Path(log_path) if log_path else None
        self.entries: list[LogEntry] = []

        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, level: str, component: str, event: str, data: dict[str, Any] | None = None) -> LogEntry:
        entry = LogEntry(
            timestamp=time.time(),
            level=level,
            component=component,
            event=event,
            data=data,
        )
        self.entries.append(entry)

        if self.log_path:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(asdict(entry)) + "\n")

        return entry

    def info(self, component: str, event: str, data: dict[str, Any] | None = None) -> LogEntry:
        return self.log("INFO", component, event, data)

    def error(self, component: str, event: str, data: dict[str, Any] | None = None) -> LogEntry:
        return self.log("ERROR", component, event, data)

    def warning(self, component: str, event: str, data: dict[str, Any] | None = None) -> LogEntry:
        return self.log("WARNING", component, event, data)
