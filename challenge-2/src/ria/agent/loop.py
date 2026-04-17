"""Claude messages-API tool-use loop for the RIA planner.

Two modes:

* **Live**: talks to Anthropic. Needs ``ANTHROPIC_API_KEY``. Opus 4.7, up to
  ``MAX_ITERATIONS`` = 15 tool-use rounds. Records the conversation into a
  JSON fixture when ``record_path`` is provided.
* **Replay**: reads a committed fixture (``tests/fixtures/replay/*.json``)
  and re-plays the assistant turns, dispatching each ``tool_use`` against
  locally-wired tool impls. Determinism: same input fixture + same tool
  code → same report.

The replay format is intentionally a subset of the messages API shape so a
recording step can dump raw responses without reshaping.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, MutableMapping

logger = logging.getLogger(__name__)

MODEL = "claude-opus-4-7"
MAX_ITERATIONS = 15


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "get_prices",
        "description": (
            "Return the last N NYSE trading days of OHLCV prices for the "
            "given tickers. `window_days` counts trading days."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
                "window_days": {"type": "integer", "minimum": 1},
            },
            "required": ["tickers", "window_days"],
        },
    },
    {
        "name": "get_news",
        "description": (
            "Return news articles for `ticker` published within "
            "`last_n_days` of the fixture's latest pub_date."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "last_n_days": {"type": "integer", "minimum": 1},
            },
            "required": ["ticker", "last_n_days"],
        },
    },
    {
        "name": "rag_search",
        "description": (
            "Semantic search over the SEC filings corpus (pgvector HNSW). "
            "IMPORTANT: authors queries in ENGLISH only — MiniLM-L6-v2 is "
            "English-first. top_k defaults to 5."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1, "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "emit_report",
        "description": (
            "Write the final Markdown report and return its path. Citations "
            "list MUST have ≥ 2 entries (URL or `accession:<id>`). Title's "
            "first 200 chars MUST contain one of: BUY/HOLD/REDUCE/WATCH/REVIEW."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "heading": {"type": "string"},
                            "body": {"type": "string"},
                        },
                        "required": ["heading", "body"],
                    },
                    "minItems": 1,
                },
                "citations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                },
                "ticker_summary": {"type": "string"},
            },
            "required": ["title", "sections", "citations"],
        },
    },
]

TOOL_NAMES: set[str] = {t["name"] for t in TOOL_SCHEMAS}


@dataclass
class LoopResult:
    """Summary returned by ``run_agent`` (both live and replay)."""
    turns: int
    report_path: Path | None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    replay: bool = False
    final_text: str = ""
    stop_reason: str | None = None


# ---- tool dispatcher -------------------------------------------------------

def dispatch_tool(
    name: str,
    arguments: Mapping[str, Any],
    tools: Mapping[str, Callable[..., Any]],
) -> Any:
    """Invoke ``tools[name](**arguments)``. Raises ``ValueError`` on unknown."""
    if name not in tools:
        raise ValueError(f"unknown tool: {name}")
    return tools[name](**arguments)


# ---- replay ----------------------------------------------------------------

def _iter_assistant_turns(fixture: MutableMapping[str, Any]):
    for turn in fixture.get("turns", []):
        asst = turn.get("assistant") or {}
        content = asst.get("content") or []
        yield asst, content


def _run_replay(
    replay_path: Path,
    tools: Mapping[str, Callable[..., Any]],
) -> LoopResult:
    if not replay_path.exists():
        raise FileNotFoundError(f"replay fixture missing: {replay_path}")
    fixture = json.loads(replay_path.read_text())

    tool_calls: list[dict[str, Any]] = []
    final_text = ""
    report_path: Path | None = None
    n_turns = 0
    stop_reason: str | None = None

    for asst, content in _iter_assistant_turns(fixture):
        n_turns += 1
        stop_reason = asst.get("stop_reason")
        for block in content:
            btype = block.get("type")
            if btype == "text":
                final_text = block.get("text", "")
            elif btype == "tool_use":
                name = block["name"]
                args = block.get("input", {}) or {}
                result = dispatch_tool(name, args, tools)
                tool_calls.append({"name": name, "input": args, "result": result})
                if name == "emit_report" and isinstance(result, (str, Path)) and result:
                    report_path = Path(result)
    return LoopResult(
        turns=n_turns,
        report_path=report_path,
        tool_calls=tool_calls,
        replay=True,
        final_text=final_text,
        stop_reason=stop_reason,
    )


# ---- live ------------------------------------------------------------------

def _serialize_tool_result(result: Any) -> str:
    """Coerce a tool result into a JSON string for a tool_result content block."""
    if isinstance(result, (str, int, float, bool)) or result is None:
        return json.dumps(result)
    try:
        return json.dumps(result, default=str)
    except TypeError:
        return json.dumps(str(result))


def _run_live(
    system_prompt: str,
    user_message: str,
    tools: Mapping[str, Callable[..., Any]],
    *,
    client: Any | None,
    model: str,
    max_iterations: int,
    record_path: Path | None = None,
) -> LoopResult:
    try:
        from anthropic import Anthropic
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("anthropic SDK not installed") from e

    client = client or Anthropic()
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": user_message},
    ]

    tool_calls: list[dict[str, Any]] = []
    recorded_turns: list[dict[str, Any]] = []
    final_text = ""
    report_path: Path | None = None
    stop_reason: str | None = None

    for iteration in range(max_iterations):
        resp = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        stop_reason = resp.stop_reason
        # serialize content blocks
        content_blocks: list[dict[str, Any]] = []
        for block in resp.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                content_blocks.append({"type": "text", "text": block.text})
                final_text = block.text
            elif btype == "tool_use":
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
        recorded_turns.append(
            {"assistant": {"id": resp.id, "stop_reason": stop_reason, "content": content_blocks}}
        )
        messages.append({"role": "assistant", "content": content_blocks})

        if stop_reason != "tool_use":
            break

        # dispatch all tool_use blocks in this turn and append a single user
        # message containing the tool_result(s).
        tool_results: list[dict[str, Any]] = []
        for block in content_blocks:
            if block.get("type") != "tool_use":
                continue
            name = block["name"]
            args = block.get("input", {}) or {}
            try:
                result = dispatch_tool(name, args, tools)
                serialized = _serialize_tool_result(result)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": serialized,
                    }
                )
                tool_calls.append({"name": name, "input": args, "result": result})
                if name == "emit_report" and isinstance(result, (str, Path)) and result:
                    report_path = Path(result)
            except Exception as e:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "is_error": True,
                        "content": f"tool error: {e}",
                    }
                )
        messages.append({"role": "user", "content": tool_results})
    else:
        logger.warning("agent loop hit max_iterations=%d", max_iterations)

    if record_path is not None:
        record_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "_note": "auto-recorded by ria.agent.loop — safe to replay via run_agent(replay_path=...)",
            "model": model,
            "system": system_prompt,
            "user": user_message,
            "turns": recorded_turns,
        }
        record_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    return LoopResult(
        turns=len(recorded_turns),
        report_path=report_path,
        tool_calls=tool_calls,
        replay=False,
        final_text=final_text,
        stop_reason=stop_reason,
    )


# ---- public entry ----------------------------------------------------------

def run_agent(
    system_prompt: str,
    user_message: str,
    *,
    replay_path: Path | None = None,
    tools: Mapping[str, Callable[..., Any]] | None = None,
    client: Any | None = None,
    model: str = MODEL,
    max_iterations: int = MAX_ITERATIONS,
    record_path: Path | None = None,
) -> LoopResult:
    """Run the Claude tool-use loop (live) or replay a committed exchange."""
    tools = dict(tools) if tools else {}
    if replay_path is not None:
        return _run_replay(Path(replay_path), tools)
    return _run_live(
        system_prompt,
        user_message,
        tools,
        client=client,
        model=model,
        max_iterations=max_iterations,
        record_path=record_path,
    )
