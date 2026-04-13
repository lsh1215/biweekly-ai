"""Verifier — judges pick/place success using camera images.

Uses claude -p (via ClaudeWrapper) for vision-based verification,
with mock mode for testing.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from src.common.types import VerificationResult
from src.orchestrator.claude_wrapper import ClaudeWrapper


class Verifier:
    """Vision-based verification of pick/place actions."""

    def __init__(
        self,
        mock_mode: bool = False,
        mock_success: bool = True,
        claude: ClaudeWrapper | None = None,
    ):
        self.mock_mode = mock_mode
        self.mock_success = mock_success
        self.claude = claude or ClaudeWrapper(mock_mode=mock_mode)

    def verify_pick(
        self,
        image: np.ndarray,
        item_name: str,
        save_dir: str | None = None,
    ) -> VerificationResult:
        """Verify whether a pick action was successful.

        Args:
            image: Post-pick camera image (H, W, 3).
            item_name: Name of the item that was picked.
            save_dir: Optional directory to save the image for Claude analysis.

        Returns:
            VerificationResult with success, confidence, reason.
        """
        if self.mock_mode:
            return self._mock_verify_pick(item_name)

        # Save image for Claude vision analysis
        image_path = self._save_image(image, save_dir, f"verify_pick_{item_name}.png")

        response = self.claude.verify_pick(image_path, item_name)
        return VerificationResult(
            success=response.get("success", False),
            confidence=response.get("confidence", 0.0),
            reason=response.get("reason", ""),
            suggested_action=self._suggest_action(response),
        )

    def verify_place(
        self,
        image: np.ndarray,
        item_name: str,
        save_dir: str | None = None,
    ) -> VerificationResult:
        """Verify whether an item was placed in the collection box.

        Args:
            image: Post-place camera image.
            item_name: Name of the item.
            save_dir: Optional save directory.

        Returns:
            VerificationResult.
        """
        if self.mock_mode:
            return self._mock_verify_place(item_name)

        image_path = self._save_image(image, save_dir, f"verify_place_{item_name}.png")

        response = self.claude.analyze_image(
            image_path,
            f"Is the '{item_name}' in the collection box? "
            f"Respond JSON: {{\"success\": bool, \"confidence\": float, \"reason\": str}}",
        )
        return VerificationResult(
            success=response.get("success", False),
            confidence=response.get("confidence", 0.0),
            reason=response.get("reason", ""),
            suggested_action=self._suggest_action(response),
        )

    def verify_grip(
        self,
        image: np.ndarray,
        item_name: str,
        save_dir: str | None = None,
    ) -> VerificationResult:
        """Verify whether the gripper is holding the object.

        Args:
            image: Camera image of the gripper area.
            item_name: Name of the item.
            save_dir: Optional save directory.

        Returns:
            VerificationResult.
        """
        if self.mock_mode:
            if self.mock_success:
                return VerificationResult(
                    success=True,
                    confidence=0.9,
                    reason=f"Gripper is holding {item_name}",
                    suggested_action="",
                )
            return VerificationResult(
                success=False,
                confidence=0.85,
                reason=f"Gripper appears empty, {item_name} not held",
                suggested_action="retry",
            )

        image_path = self._save_image(image, save_dir, f"verify_grip_{item_name}.png")

        response = self.claude.analyze_image(
            image_path,
            f"Is the robot gripper holding the '{item_name}'? "
            f"Respond JSON: {{\"success\": bool, \"confidence\": float, \"reason\": str}}",
        )
        return VerificationResult(
            success=response.get("success", False),
            confidence=response.get("confidence", 0.0),
            reason=response.get("reason", ""),
            suggested_action="retry" if not response.get("success", False) else "",
        )

    def _mock_verify_pick(self, item_name: str) -> VerificationResult:
        """Mock pick verification."""
        if self.mock_success:
            return VerificationResult(
                success=True,
                confidence=0.92,
                reason=f"{item_name} successfully picked from shelf",
                suggested_action="",
            )
        return VerificationResult(
            success=False,
            confidence=0.8,
            reason=f"Failed to pick {item_name} — grip missed the object",
            suggested_action="retry",
        )

    def _mock_verify_place(self, item_name: str) -> VerificationResult:
        """Mock place verification."""
        if self.mock_success:
            return VerificationResult(
                success=True,
                confidence=0.95,
                reason=f"{item_name} placed in collection box",
                suggested_action="",
            )
        return VerificationResult(
            success=False,
            confidence=0.75,
            reason=f"{item_name} dropped before reaching collection box",
            suggested_action="replan",
        )

    def _suggest_action(self, response: dict[str, Any]) -> str:
        """Suggest next action based on verification response."""
        if response.get("success", False):
            return ""

        reason = response.get("reason", "").lower()
        if "drop" in reason or "fall" in reason:
            return "replan"
        if "miss" in reason or "empty" in reason or "fail" in reason:
            return "retry"
        return "skip"

    def _save_image(
        self, image: np.ndarray, save_dir: str | None, filename: str,
    ) -> str:
        """Save image to disk for Claude analysis."""
        if save_dir:
            path = Path(save_dir) / filename
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            tmp = tempfile.mktemp(suffix=".png")
            path = Path(tmp)

        img = Image.fromarray(image)
        img.save(str(path))
        return str(path)
