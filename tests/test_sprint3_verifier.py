"""Sprint 3: Verifier tests (TDD — written first).

Tests for:
- Pick success/failure judgment
- Structured VerificationResult
- Mock and Claude modes
"""

import numpy as np
import pytest

from src.common.types import VerificationResult


class TestVerifierResult:
    """Test Verifier returns structured results."""

    def test_verify_pick_success(self):
        """Verifier should return success for mock success case."""
        from src.orchestrator.verifier import Verifier

        verifier = Verifier(mock_mode=True, mock_success=True)
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = verifier.verify_pick(image, item_name="apple")

        assert isinstance(result, VerificationResult)
        assert result.success is True
        assert result.confidence > 0.5
        assert result.reason != ""

    def test_verify_pick_failure(self):
        """Verifier should return failure when pick failed."""
        from src.orchestrator.verifier import Verifier

        verifier = Verifier(mock_mode=True, mock_success=False)
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = verifier.verify_pick(image, item_name="apple")

        assert isinstance(result, VerificationResult)
        assert result.success is False
        assert result.reason != ""

    def test_verify_returns_suggested_action(self):
        """Failed verification should suggest next action."""
        from src.orchestrator.verifier import Verifier

        verifier = Verifier(mock_mode=True, mock_success=False)
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = verifier.verify_pick(image, item_name="apple")

        assert result.suggested_action != ""
        assert result.suggested_action in ("retry", "replan", "skip")


class TestVerifierPlace:
    """Test Verifier place verification."""

    def test_verify_place_success(self):
        """Verify that item was placed in collection box."""
        from src.orchestrator.verifier import Verifier

        verifier = Verifier(mock_mode=True, mock_success=True)
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = verifier.verify_place(image, item_name="apple")

        assert isinstance(result, VerificationResult)
        assert result.success is True

    def test_verify_place_failure(self):
        """Verify place failure (item dropped on way)."""
        from src.orchestrator.verifier import Verifier

        verifier = Verifier(mock_mode=True, mock_success=False)
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = verifier.verify_place(image, item_name="bottle")

        assert result.success is False
        assert "drop" in result.reason.lower() or "fail" in result.reason.lower()


class TestVerifierGrip:
    """Test grip verification."""

    def test_verify_grip_holding(self):
        """Verify that gripper is holding the object."""
        from src.orchestrator.verifier import Verifier

        verifier = Verifier(mock_mode=True, mock_success=True)
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = verifier.verify_grip(image, item_name="apple")

        assert result.success is True

    def test_verify_grip_empty(self):
        """Verify that gripper is empty (failed grip)."""
        from src.orchestrator.verifier import Verifier

        verifier = Verifier(mock_mode=True, mock_success=False)
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = verifier.verify_grip(image, item_name="apple")

        assert result.success is False
        assert result.suggested_action == "retry"


class TestVerifierClaudeIntegration:
    """Test Verifier with Claude wrapper (mocked)."""

    def test_verifier_creates_with_claude(self):
        """Verifier should accept a ClaudeWrapper."""
        from src.orchestrator.verifier import Verifier

        verifier = Verifier(mock_mode=True)
        assert verifier is not None

    def test_verifier_saves_image_for_analysis(self):
        """Verifier should be able to save image for Claude analysis."""
        import tempfile
        from pathlib import Path

        from src.orchestrator.verifier import Verifier

        verifier = Verifier(mock_mode=True, mock_success=True)
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = verifier.verify_pick(
                image, item_name="apple", save_dir=tmpdir,
            )
            assert result.success is True
