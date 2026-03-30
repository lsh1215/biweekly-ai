"""LLM Reasoning Trace — captures and displays agent reasoning steps.

Captures planner/verifier reasoning and renders with rich terminal output.
"""

from __future__ import annotations

import time
from typing import Any


class ReasoningTrace:
    """Captures and formats LLM reasoning steps for display."""

    def __init__(self):
        self.entries: list[dict[str, Any]] = []
        self._start_time = time.time()

    def add(
        self,
        component: str,
        reasoning: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Add a reasoning step.

        Args:
            component: Which component produced this reasoning (planner/verifier).
            reasoning: The reasoning text.
            data: Optional structured data.
        """
        self.entries.append({
            "timestamp": time.time(),
            "elapsed": time.time() - self._start_time,
            "component": component,
            "reasoning": reasoning,
            "data": data,
        })

    def render_text(self) -> str:
        """Render the trace as plain text."""
        lines = []
        for entry in self.entries:
            elapsed = entry["elapsed"]
            comp = entry["component"].upper()
            reasoning = entry["reasoning"]
            line = f"[{elapsed:6.2f}s] {comp:12s} | {reasoning}"
            if entry.get("data"):
                line += f"\n{'':>22}data: {entry['data']}"
            lines.append(line)
        return "\n".join(lines)

    def render_rich(self) -> None:
        """Render the trace using rich library for colorful terminal output."""
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text

            console = Console()

            table = Table(
                title="LLM Reasoning Trace",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Time", style="cyan", width=8)
            table.add_column("Component", style="green", width=12)
            table.add_column("Reasoning", style="white")

            COMPONENT_COLORS = {
                "planner": "blue",
                "verifier": "yellow",
                "recovery": "red",
                "loop": "green",
            }

            for entry in self.entries:
                elapsed = f"{entry['elapsed']:.2f}s"
                comp = entry["component"]
                color = COMPONENT_COLORS.get(comp, "white")
                comp_text = Text(comp.upper(), style=f"bold {color}")

                reasoning = entry["reasoning"]
                if entry.get("data"):
                    reasoning += f"\n  [dim]{entry['data']}[/dim]"

                table.add_row(elapsed, comp_text, reasoning)

            console.print(Panel(table, border_style="bright_blue"))

        except ImportError:
            # Fallback to plain text
            print(self.render_text())

    def to_dict(self) -> dict[str, Any]:
        """Export trace as dict for serialization."""
        return {
            "entries": self.entries,
            "total_steps": len(self.entries),
            "total_time": self.entries[-1]["elapsed"] if self.entries else 0,
        }

    def clear(self) -> None:
        """Clear all entries."""
        self.entries.clear()
        self._start_time = time.time()
