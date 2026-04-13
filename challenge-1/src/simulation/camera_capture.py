"""Camera image capture from Gazebo simulation.

Captures images from the overhead camera via ZMQ bridge or generates
test images for mock mode.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


class CameraCapture:
    """Capture images from the simulated camera.

    Supports two modes:
    - zmq: Receive images through ZMQ bridge from Docker
    - mock: Generate synthetic test images
    """

    def __init__(self, mode: str = "mock", bridge: Any = None,
                 width: int = 640, height: int = 480):
        self.mode = mode
        self.bridge = bridge
        self.width = width
        self.height = height
        self._frame_count = 0

    def capture(self) -> np.ndarray | None:
        """Capture a single frame from the camera.

        Returns:
            RGB numpy array (H, W, 3) or None if capture failed.
        """
        if self.mode == "zmq" and self.bridge:
            return self.bridge.receive_image(timeout=5000)

        # Mock mode: generate a synthetic image
        return self._generate_mock_image()

    def capture_and_save(self, path: str | Path) -> bool:
        """Capture a frame and save to disk.

        Args:
            path: Output image path (supports PNG, JPG).

        Returns:
            True if saved successfully.
        """
        image = self.capture()
        if image is None:
            return False

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        img = Image.fromarray(image)
        img.save(str(path))
        return True

    def _generate_mock_image(self) -> np.ndarray:
        """Generate a synthetic warehouse image for testing.

        Creates a simple overhead view with colored rectangles
        representing shelves and circles for objects.
        """
        w, h = self.width, self.height
        sx, sy = w / 640.0, h / 480.0  # scale factors relative to default

        image = np.ones((h, w, 3), dtype=np.uint8) * 180  # gray floor

        def s(x, y):
            return int(x * sx), int(y * sy)

        # Draw shelves as brown rectangles
        shelves = [(380, 200, 420, 280), (380, 60, 420, 140), (380, 320, 420, 400)]
        for x1, y1, x2, y2 in shelves:
            x1s, y1s = s(x1, y1)
            x2s, y2s = s(x2, y2)
            image[y1s:y2s, x1s:x2s] = [139, 90, 43]

        # Draw objects as colored circles
        objects = [
            (390, 220, [255, 0, 0]), (410, 260, [0, 128, 255]),
            (390, 80, [0, 180, 0]), (410, 120, [200, 150, 50]),
            (390, 340, [200, 200, 200]), (410, 380, [255, 255, 255]),
        ]
        r = max(3, int(8 * min(sx, sy)))
        for ox, oy, color in objects:
            cx, cy = s(ox, oy)
            y_lo, y_hi = max(0, cy - r), min(h, cy + r)
            x_lo, x_hi = max(0, cx - r), min(w, cx + r)
            for y in range(y_lo, y_hi):
                for x in range(x_lo, x_hi):
                    if (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2:
                        image[y, x] = color

        # Draw collection box
        bx1, by1 = s(80, 220)
        bx2, by2 = s(120, 260)
        image[by1:by2, bx1:bx2] = [60, 60, 60]

        # Draw robot base
        rcx, rcy = s(320, 240)
        rr = max(4, int(12 * min(sx, sy)))
        for y in range(max(0, rcy - rr), min(h, rcy + rr)):
            for x in range(max(0, rcx - rr), min(w, rcx + rr)):
                if (x - rcx) ** 2 + (y - rcy) ** 2 <= rr ** 2:
                    image[y, x] = [80, 80, 80]

        self._frame_count += 1
        return image
