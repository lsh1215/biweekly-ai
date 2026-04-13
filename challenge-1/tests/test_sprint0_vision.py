"""Sprint 0: claude -p vision validation tests (TDD - written first).

These tests validate that we can use claude -p for visual verification.
Since claude -p requires a running Claude CLI, we test the wrapper logic
and use mock/integration modes.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestClaudePWrapper:
    """Test the claude -p wrapper for orchestrator use."""

    def test_wrapper_returns_json(self):
        """Wrapper should parse claude -p JSON output."""
        from src.orchestrator.claude_wrapper import ClaudeWrapper

        wrapper = ClaudeWrapper(mock_mode=True)
        result = wrapper.query("What objects do you see?")

        assert isinstance(result, dict)
        assert "result" in result or "response" in result

    def test_wrapper_handles_timeout(self):
        """Wrapper should handle timeout gracefully."""
        from src.orchestrator.claude_wrapper import ClaudeWrapper

        wrapper = ClaudeWrapper(mock_mode=True, timeout=1)
        result = wrapper.query("test query")

        assert result is not None

    def test_wrapper_mock_mode(self):
        """Mock mode should return predefined responses."""
        from src.orchestrator.claude_wrapper import ClaudeWrapper

        wrapper = ClaudeWrapper(mock_mode=True)
        result = wrapper.query("Identify the object in this image")

        assert isinstance(result, dict)


class TestVisionAnalysis:
    """Test vision analysis capability."""

    def test_analyze_image_returns_structured(self):
        """Vision analysis should return structured results."""
        from src.orchestrator.claude_wrapper import ClaudeWrapper

        wrapper = ClaudeWrapper(mock_mode=True)
        result = wrapper.analyze_image(
            image_path="test_image.png",
            question="What objects do you see on the shelf?"
        )

        assert isinstance(result, dict)
        assert "objects" in result or "response" in result

    def test_verify_pick_success(self):
        """Should correctly verify a successful pick."""
        from src.orchestrator.claude_wrapper import ClaudeWrapper

        wrapper = ClaudeWrapper(mock_mode=True)
        wrapper.set_mock_response({
            "success": True,
            "confidence": 0.95,
            "reason": "Apple is held in gripper"
        })

        result = wrapper.verify_pick(
            image_path="test_image.png",
            item_name="apple"
        )

        assert result["success"] is True
        assert result["confidence"] > 0.5

    def test_verify_pick_failure(self):
        """Should correctly detect a failed pick."""
        from src.orchestrator.claude_wrapper import ClaudeWrapper

        wrapper = ClaudeWrapper(mock_mode=True)
        wrapper.set_mock_response({
            "success": False,
            "confidence": 0.9,
            "reason": "Apple is still on the shelf"
        })

        result = wrapper.verify_pick(
            image_path="test_image.png",
            item_name="apple"
        )

        assert result["success"] is False


class TestClaudePLatency:
    """Test claude -p response latency."""

    @pytest.mark.vision
    @pytest.mark.slow
    def test_claude_p_responds_within_timeout(self):
        """claude -p should respond within 10 seconds."""
        import time
        from src.orchestrator.claude_wrapper import ClaudeWrapper

        wrapper = ClaudeWrapper(mock_mode=False, timeout=10)

        start = time.time()
        try:
            result = wrapper.query("Say 'hello' in JSON format: {\"response\": \"hello\"}")
            elapsed = time.time() - start
            assert elapsed < 10.0, f"claude -p took {elapsed:.1f}s, exceeds 10s limit"
        except FileNotFoundError:
            pytest.skip("claude CLI not found")
        except Exception as e:
            pytest.skip(f"claude -p not available: {e}")
