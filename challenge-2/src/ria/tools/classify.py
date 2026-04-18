"""Severity classifier — Haiku 4.5 wrapper.

Returns ``{"severity": "P0"|"P1"|"P2", "rationale": str}``.

Classification rules baked into the system prompt:
  * P0 — event directly hits a ticker the user holds (earnings miss, M&A,
    SEC filing, lawsuit, guidance change for that exact ticker).
  * P1 — sector / macro / supplier-chain story that affects holdings only
    indirectly. v1 defers (next planned cycle) — still classified P1 here.
  * P2 — generic noise (random fintwit posts, opinion pieces, off-topic).

Two execution modes:

* **Live** — needs ``ANTHROPIC_API_KEY``. Small Haiku call, max_tokens=200.
  Total prompt size capped at ~1500 input tokens (raw_text truncated).
* **Replay** — looks up ``<replay_dir>/<event_id>.json`` and returns it
  verbatim. Lets tests + the no-key overnight path stay deterministic.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ria.agent.event import Event
from ria.models import Portfolio

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5"
MAX_INPUT_CHARS = 6000  # ~ 1500 tokens budget for prompt + event text
MAX_OUTPUT_TOKENS = 200

Severity = Literal["P0", "P1", "P2"]
_VALID_SEVERITIES: tuple[Severity, ...] = ("P0", "P1", "P2")

SYSTEM_PROMPT = """You are a market-event severity classifier for a long-only US equity
investment agent. The user holds a small portfolio of US tickers.

Classify each event into one of three severities.

P0 — DIRECT HIT on a holding. The event is about a ticker the user owns:
     earnings miss/beat, guidance change, M&A, SEC enforcement, large
     lawsuit, executive resignation, product recall. Triggers an immediate
     interrupt report.
P1 — RELATED MACRO / SECTOR. The event affects an industry or supply chain
     the holdings sit in but does not name a held ticker directly. Examples:
     "EV demand softening", "semiconductor export curbs", "Fed rate
     decision". v1 defers these to the next planned cycle.
P2 — NOISE. Generic punditry, social-media speculation, off-topic. Ignore.

Output format — STRICT JSON, no prose, no markdown fences:
{"severity": "P0", "rationale": "<1-2 sentence English reason>"}

Bias toward P2 when the source is anonymous social media; only escalate to
P0 if a held ticker is named explicitly with a concrete factual claim."""


@dataclass(frozen=True)
class ClassifierResult:
    severity: Severity
    rationale: str

    def to_dict(self) -> dict[str, str]:
        return {"severity": self.severity, "rationale": self.rationale}


def _holdings(portfolio: Portfolio) -> list[str]:
    return [p.ticker for p in portfolio.positions]


def build_user_prompt(event: Event, portfolio: Portfolio) -> str:
    """Compose the user message, truncating raw_text to the input budget."""
    holdings = _holdings(portfolio)
    raw = event.raw_text
    if len(raw) > MAX_INPUT_CHARS:
        raw = raw[:MAX_INPUT_CHARS] + "...[truncated]"
    affected = event.expected_affected_tickers or []
    return (
        f"Holdings: {holdings}\n"
        f"Event id: {event.event_id}\n"
        f"Source: {event.source_type}\n"
        f"Timestamp: {event.ts_utc.isoformat()}\n"
        f"Pre-tagged tickers (advisory only): {affected}\n"
        f"Raw text:\n---\n{raw}\n---\n"
        "Classify and respond with JSON only."
    )


def _coerce_severity(value: Any) -> Severity:
    s = str(value).strip().upper()
    if s not in _VALID_SEVERITIES:
        raise ValueError(f"invalid severity: {value!r} (expected one of {_VALID_SEVERITIES})")
    return s  # type: ignore[return-value]


def parse_response_text(text: str) -> ClassifierResult:
    """Parse the model's JSON output — tolerates surrounding whitespace / fences."""
    cleaned = text.strip()
    # tolerate ```json ... ``` fences just in case
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    data = json.loads(cleaned)
    sev = _coerce_severity(data.get("severity"))
    rationale = str(data.get("rationale", "")).strip() or "(no rationale)"
    return ClassifierResult(severity=sev, rationale=rationale)


def _parse_anthropic_response(resp: Any) -> ClassifierResult:
    text = ""
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            text = block.text
            break
    if not text:
        raise RuntimeError("Haiku response had no text block")
    return parse_response_text(text)


def _replay_response(event_id: str, replay_dir: Path) -> ClassifierResult:
    fp = Path(replay_dir) / f"{event_id}.json"
    if not fp.exists():
        raise FileNotFoundError(f"classify replay missing: {fp}")
    data = json.loads(fp.read_text())
    return ClassifierResult(
        severity=_coerce_severity(data["severity"]),
        rationale=str(data.get("rationale", "")).strip() or "(no rationale)",
    )


def classify_severity(
    event: Event,
    portfolio: Portfolio,
    *,
    client: Any | None = None,
    replay_dir: Path | None = None,
    model: str = MODEL,
) -> ClassifierResult:
    """Return severity + rationale. Replay-mode skips the API call."""
    if replay_dir is not None:
        return _replay_response(event.event_id, Path(replay_dir))

    user_msg = build_user_prompt(event, portfolio)

    if client is None:
        from anthropic import Anthropic  # type: ignore[import-not-found]
        client = Anthropic()

    resp = client.messages.create(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return _parse_anthropic_response(resp)
