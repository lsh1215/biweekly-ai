"""Sprint 5: Expansions + Demo + Polish tests.

TDD — written BEFORE implementation.
Tests: structured logging/replay, reasoning trace, A/B comparison,
adversarial demo, benchmark.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.common.types import Order


# ── Structured Logging + Replay ─────────────────────────────────────

class TestStructuredLogger:
    """Enhanced StructuredLogger with JSONL output and replay."""

    def test_log_writes_jsonl(self):
        from src.common.logger import StructuredLogger
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name

        logger = StructuredLogger(log_path=path)
        logger.info("test", "hello", {"key": "value"})
        logger.info("test", "world")

        lines = Path(path).read_text().strip().split("\n")
        assert len(lines) == 2
        entry = json.loads(lines[0])
        assert entry["level"] == "INFO"
        assert entry["component"] == "test"
        assert entry["event"] == "hello"
        assert entry["data"]["key"] == "value"
        assert "timestamp" in entry

    def test_log_levels(self):
        from src.common.logger import StructuredLogger
        logger = StructuredLogger()
        e1 = logger.info("c", "info event")
        e2 = logger.warning("c", "warn event")
        e3 = logger.error("c", "error event")
        assert e1.level == "INFO"
        assert e2.level == "WARNING"
        assert e3.level == "ERROR"

    def test_in_memory_entries(self):
        from src.common.logger import StructuredLogger
        logger = StructuredLogger()
        logger.info("a", "event1")
        logger.info("b", "event2")
        assert len(logger.entries) == 2


class TestReplaySystem:
    """Replay from JSONL log files."""

    def test_replay_loads_log(self):
        from scripts.replay import load_log

        with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
            f.write(json.dumps({"timestamp": 1.0, "level": "INFO", "component": "loop", "event": "start", "data": None}) + "\n")
            f.write(json.dumps({"timestamp": 2.0, "level": "INFO", "component": "loop", "event": "end", "data": None}) + "\n")
            path = f.name

        entries = load_log(path)
        assert len(entries) == 2
        assert entries[0]["event"] == "start"
        assert entries[1]["event"] == "end"

    def test_replay_formats_timeline(self):
        from scripts.replay import format_timeline

        entries = [
            {"timestamp": 1000.0, "level": "INFO", "component": "loop", "event": "start", "data": None},
            {"timestamp": 1001.5, "level": "INFO", "component": "vla", "event": "inference", "data": {"item": "apple"}},
        ]
        lines = format_timeline(entries)
        assert len(lines) == 2
        assert "loop" in lines[0]
        assert "vla" in lines[1]


# ── LLM Reasoning Trace ────────────────────────────────────────────

class TestReasoningTrace:
    """Reasoning trace capture and formatting."""

    def test_trace_captures_entries(self):
        from src.orchestrator.reasoning_trace import ReasoningTrace

        trace = ReasoningTrace()
        trace.add("planner", "Parsing order: 3 items identified", {"items": ["apple", "bottle", "book"]})
        trace.add("verifier", "Pick verified: apple in gripper")
        assert len(trace.entries) == 2
        assert trace.entries[0]["component"] == "planner"

    def test_trace_render_text(self):
        from src.orchestrator.reasoning_trace import ReasoningTrace

        trace = ReasoningTrace()
        trace.add("planner", "Planning pick sequence")
        trace.add("verifier", "Verification passed")
        text = trace.render_text()
        assert "planner" in text.lower() or "PLANNER" in text
        assert "verifier" in text.lower() or "VERIFIER" in text

    def test_trace_to_dict(self):
        from src.orchestrator.reasoning_trace import ReasoningTrace

        trace = ReasoningTrace()
        trace.add("planner", "test", {"key": "val"})
        d = trace.to_dict()
        assert "entries" in d
        assert len(d["entries"]) == 1


# ── A/B Comparison ──────────────────────────────────────────────────

class TestABComparison:
    """A/B comparison between VLA-only and Agent+VLA."""

    def test_run_vla_only_benchmark(self):
        from scripts.benchmark import run_vla_only

        result = run_vla_only(num_items=3)
        assert "success_count" in result
        assert "total" in result
        assert result["total"] == 3
        assert "success_rate" in result

    def test_run_agent_vla_benchmark(self):
        from scripts.benchmark import run_agent_vla

        result = run_agent_vla(num_items=3)
        assert "success_count" in result
        assert "total" in result
        assert result["total"] == 3
        assert "success_rate" in result

    def test_agent_vla_outperforms_vla_only(self):
        """Agent+VLA should have higher success rate due to replanning."""
        from scripts.benchmark import run_vla_only, run_agent_vla

        vla_result = run_vla_only(num_items=6)
        agent_result = run_agent_vla(num_items=6)
        # Agent+VLA should match or exceed VLA-only
        assert agent_result["success_rate"] >= vla_result["success_rate"]


class TestVisualization:
    """Matplotlib chart generation."""

    def test_generate_comparison_chart(self):
        from scripts.visualize_comparison import generate_chart

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "chart.png"
            vla_data = {"success_rate": 0.5, "avg_time": 1.2}
            agent_data = {"success_rate": 0.83, "avg_time": 2.5}
            generate_chart(vla_data, agent_data, str(output_path))
            assert output_path.exists()
            assert output_path.stat().st_size > 1000  # real PNG


# ── Adversarial Demo ────────────────────────────────────────────────

class TestAdversarialDemo:
    """Interactive adversarial: object teleport during picking."""

    def test_teleport_object(self):
        from scripts.demo_adversarial import AdversarialDemo

        demo = AdversarialDemo(mock_mode=True)
        result = demo.teleport_object("apple", new_x=1.0, new_y=2.0, new_z=0.5)
        assert result["success"] is True
        assert result["object"] == "apple"

    def test_adversarial_scenario_detects_and_recovers(self):
        from scripts.demo_adversarial import AdversarialDemo

        demo = AdversarialDemo(mock_mode=True)
        report = demo.run_scenario("apple")
        assert "detected" in report
        assert "recovered" in report
        assert report["detected"] is True


# ── Benchmark ───────────────────────────────────────────────────────

class TestBenchmark:
    """Benchmark produces structured results."""

    def test_benchmark_full_run(self):
        from scripts.benchmark import run_benchmark

        results = run_benchmark(num_items=3, num_trials=2)
        assert "vla_only" in results
        assert "agent_vla" in results
        assert "trials" in results
        assert results["trials"] == 2
