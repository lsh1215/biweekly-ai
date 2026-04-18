"""Event model — synthetic market events read from `tests/fixtures/synthetic_events/*.json`.

Schema mirrors the design doc's Event Loop Semantics section. Pydantic v2 strict.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Event(BaseModel):
    model_config = ConfigDict(frozen=False, strict=False)

    event_id: str = Field(..., min_length=1)
    ts_utc: datetime
    source_type: str = Field(..., min_length=1)
    raw_text: str = Field(..., min_length=1)
    expected_affected_tickers: list[str] = Field(default_factory=list)
    expected_severity: str | None = None
    ground_truth_action_hint: str | None = None

    @field_validator("expected_affected_tickers", mode="before")
    @classmethod
    def _normalize_tickers(cls, v):
        if v is None:
            return []
        return [t.strip().upper() for t in v if isinstance(t, str) and t.strip()]

    @classmethod
    def from_path(cls, path: Path) -> "Event":
        return cls(**json.loads(Path(path).read_text()))
