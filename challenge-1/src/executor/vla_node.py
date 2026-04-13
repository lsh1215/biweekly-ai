"""VLA inference node — loads model, preprocesses images, runs inference.

This is the main entry point for VLA model inference. It handles:
- Model loading (SmolVLA on MPS or ScriptedPolicy fallback)
- Image preprocessing for the model
- Inference timing and tracking
- Trajectory generation for pick-and-place
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from PIL import Image

from src.common.types import RobotAction
from src.executor.models.model_loader import ModelLoader


class VLANode:
    """VLA inference node for robot action prediction."""

    # Default image size for VLA models
    DEFAULT_IMAGE_SIZE = (224, 224)

    def __init__(self, model_type: str = "scripted", **model_kwargs: Any):
        """Initialize VLA node with specified model.

        Args:
            model_type: 'smolvla' or 'scripted'.
            **model_kwargs: Additional args for model loading.
        """
        self.model_type = model_type
        self.model = ModelLoader.load(model_type, **model_kwargs)
        self._ready = True
        self.last_inference_time: float = 0.0
        self._total_inferences: int = 0

    def is_ready(self) -> bool:
        """Check if the node is ready for inference."""
        return self._ready and self.model is not None

    def preprocess_image(self, image: np.ndarray | None) -> np.ndarray | None:
        """Preprocess image for VLA model input.

        Args:
            image: RGB numpy array (H, W, 3) with uint8 values.

        Returns:
            Preprocessed image as numpy array, or None if input is None.
        """
        if image is None:
            return None

        # Resize to model's expected input size
        pil_image = Image.fromarray(image)
        pil_image = pil_image.resize(self.DEFAULT_IMAGE_SIZE, Image.BILINEAR)

        # Convert back to numpy, normalize to [0, 1]
        processed = np.array(pil_image).astype(np.float32) / 255.0

        return processed

    def predict(self, image: np.ndarray | None, instruction: str) -> RobotAction:
        """Run VLA inference to predict robot action.

        Args:
            image: RGB camera image (H, W, 3) or None.
            instruction: Natural language command.

        Returns:
            RobotAction with predicted joint angles and gripper.
        """
        start = time.time()

        # Preprocess image
        processed_image = self.preprocess_image(image)

        # Run inference
        action = self.model.predict(instruction=instruction, image=processed_image)

        self.last_inference_time = time.time() - start
        self._total_inferences += 1

        return action

    def get_trajectory(self, instruction: str, image: np.ndarray | None = None) -> list[RobotAction]:
        """Generate a multi-step trajectory for pick-and-place.

        Args:
            instruction: Natural language command.
            image: Optional camera image.

        Returns:
            List of RobotAction steps.
        """
        if hasattr(self.model, 'get_trajectory'):
            return self.model.get_trajectory(instruction)

        # Default: single action
        return [self.predict(image, instruction)]

    @property
    def total_inferences(self) -> int:
        """Total number of inferences run."""
        return self._total_inferences

    @property
    def model_info(self) -> dict[str, Any]:
        """Get model information."""
        info: dict[str, Any] = {
            "type": self.model_type,
            "ready": self.is_ready(),
            "total_inferences": self._total_inferences,
            "last_inference_time": self.last_inference_time,
        }
        if self.model_type == "smolvla" and hasattr(self.model, 'device'):
            info["device"] = str(self.model.device)
        return info
