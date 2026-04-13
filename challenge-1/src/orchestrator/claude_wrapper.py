"""Wrapper for claude -p CLI for orchestrator use."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any


class ClaudeWrapper:
    """Wraps claude -p CLI calls for Planner and Verifier.

    Supports mock_mode for testing without actual Claude CLI.
    """

    def __init__(self, mock_mode: bool = False, timeout: int = 30):
        self.mock_mode = mock_mode
        self.timeout = timeout
        self._mock_response: dict[str, Any] | None = None

    def set_mock_response(self, response: dict[str, Any]) -> None:
        """Set a specific mock response for testing."""
        self._mock_response = response

    def query(self, prompt: str) -> dict[str, Any]:
        """Send a text query to claude -p and return parsed JSON."""
        if self.mock_mode:
            return self._get_mock_response(prompt)

        return self._call_claude(prompt)

    def analyze_image(self, image_path: str, question: str) -> dict[str, Any]:
        """Analyze an image with claude -p vision.

        Args:
            image_path: Path to the image file.
            question: Question about the image.

        Returns:
            Structured response with analysis results.
        """
        if self.mock_mode:
            if self._mock_response:
                return self._mock_response
            return {
                "objects": ["apple", "bottle"],
                "response": "I can see objects on the shelf.",
            }

        prompt = f"Look at the image at {image_path}. {question}. Respond in JSON."
        return self._call_claude(prompt)

    def verify_pick(self, image_path: str, item_name: str) -> dict[str, Any]:
        """Verify whether a pick action was successful.

        Args:
            image_path: Path to post-pick camera image.
            item_name: Name of the item that was picked.

        Returns:
            Dict with success, confidence, and reason.
        """
        if self.mock_mode:
            if self._mock_response:
                return self._mock_response
            return {
                "success": True,
                "confidence": 0.9,
                "reason": f"{item_name} successfully picked",
            }

        prompt = (
            f"Look at this image: {image_path}\n"
            f"Was the '{item_name}' successfully picked up by the robot gripper?\n"
            f"Respond in JSON: {{\"success\": bool, \"confidence\": float, \"reason\": str}}"
        )
        return self._call_claude(prompt)

    def _call_claude(self, prompt: str) -> dict[str, Any]:
        """Execute claude -p and parse JSON output."""
        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "json"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode != 0:
                return {"error": result.stderr, "response": result.stdout}

            # Parse the JSON output
            try:
                parsed = json.loads(result.stdout)
                # claude -p --output-format json wraps in {"type":"result", "result": "..."}
                if "result" in parsed and isinstance(parsed["result"], str):
                    inner_text = parsed["result"].strip()
                    # Strip markdown code fences if present
                    if inner_text.startswith("```"):
                        lines = inner_text.split("\n")
                        # Remove first line (```json) and last line (```)
                        lines = [l for l in lines if not l.strip().startswith("```")]
                        inner_text = "\n".join(lines).strip()
                    # Try to parse the inner result as JSON
                    try:
                        inner = json.loads(inner_text)
                        return inner
                    except json.JSONDecodeError:
                        return {"response": parsed["result"]}
                return parsed
            except json.JSONDecodeError:
                return {"response": result.stdout.strip()}

        except FileNotFoundError:
            raise FileNotFoundError("claude CLI not found. Install from code.claude.com")
        except subprocess.TimeoutExpired:
            return {"error": "timeout", "response": ""}

    def _get_mock_response(self, prompt: str) -> dict[str, Any]:
        """Return mock responses for testing."""
        if self._mock_response:
            return self._mock_response

        prompt_lower = prompt.lower()

        if "pick" in prompt_lower or "identify" in prompt_lower:
            return {
                "objects": ["apple", "bottle", "book"],
                "response": "I can identify objects on the shelves.",
            }

        if "plan" in prompt_lower or "order" in prompt_lower:
            return {
                "result": json.dumps({
                    "tasks": [
                        {"item": "apple", "shelf": "A", "action": "pick"},
                        {"item": "bottle", "shelf": "A", "action": "pick"},
                    ]
                }),
            }

        return {"result": "OK", "response": "Mock response"}
