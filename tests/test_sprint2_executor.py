"""Sprint 2: VLA Executor tests (TDD — written first).

Tests for:
- ActionConverter: VLA normalized output [-1,1] → joint angles, clipping, gripper mapping
- VLANode: image preprocessing, model inference, mock/scripted modes
- ModelLoader: SmolVLA/ScriptedPolicy factory
- End-to-end: camera → VLA → action pipeline
"""

import math

import numpy as np
import pytest

from src.common.types import RobotAction


# =============================================================================
# ActionConverter Tests
# =============================================================================
class TestActionConverter:
    """Test VLA output → robot joint command conversion."""

    def test_normalized_to_joint_angles(self):
        """Convert [-1,1] normalized outputs to joint angle range."""
        from src.executor.action_converter import ActionConverter

        converter = ActionConverter()
        # All zeros should map to midpoint of each joint's range
        normalized = [0.0] * 6
        angles = converter.normalized_to_joint_angles(normalized)

        assert len(angles) == 6
        # Each angle should be the midpoint of its joint limit range
        for i, angle in enumerate(angles):
            lo, hi = converter.joint_limits[i]
            expected_mid = (lo + hi) / 2.0
            assert abs(angle - expected_mid) < 0.01, f"Joint {i}: {angle} != {expected_mid}"

    def test_normalized_extremes(self):
        """Extreme values [-1, 1] should map to joint limits."""
        from src.executor.action_converter import ActionConverter

        converter = ActionConverter()

        # All -1 → lower limits
        angles_low = converter.normalized_to_joint_angles([-1.0] * 6)
        for i, angle in enumerate(angles_low):
            lo, _ = converter.joint_limits[i]
            assert abs(angle - lo) < 0.01

        # All +1 → upper limits
        angles_high = converter.normalized_to_joint_angles([1.0] * 6)
        for i, angle in enumerate(angles_high):
            _, hi = converter.joint_limits[i]
            assert abs(angle - hi) < 0.01

    def test_clipping_out_of_range(self):
        """Values outside [-1,1] should be clipped."""
        from src.executor.action_converter import ActionConverter

        converter = ActionConverter()
        # Values > 1 or < -1 should be clipped
        angles = converter.normalized_to_joint_angles([2.0, -2.0, 1.5, -1.5, 0.0, 0.0])

        for i, angle in enumerate(angles):
            lo, hi = converter.joint_limits[i]
            assert lo <= angle <= hi, f"Joint {i}: {angle} not in [{lo}, {hi}]"

    def test_gripper_mapping(self):
        """Gripper value [0,1] maps to width [max_width, 0]."""
        from src.executor.action_converter import ActionConverter

        converter = ActionConverter()

        # gripper=0 (VLA open) → max width
        assert converter.gripper_to_width(0.0) == pytest.approx(0.04)
        # gripper=1 (VLA closed) → 0 width
        assert converter.gripper_to_width(1.0) == pytest.approx(0.0)
        # gripper=0.5 → half width
        assert converter.gripper_to_width(0.5) == pytest.approx(0.02)

    def test_convert_robot_action(self):
        """Full conversion from VLA RobotAction to joint command."""
        from src.executor.action_converter import ActionConverter

        converter = ActionConverter()
        vla_action = RobotAction(
            joint_angles=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            gripper=0.5,
        )
        joint_positions, gripper_width = converter.convert(vla_action)

        assert len(joint_positions) == 6
        assert 0.0 <= gripper_width <= 0.04

    def test_wrong_joint_count_raises(self):
        """Should raise error for wrong number of joints."""
        from src.executor.action_converter import ActionConverter

        converter = ActionConverter()
        with pytest.raises(ValueError):
            converter.normalized_to_joint_angles([0.0] * 5)

    def test_delta_mode(self):
        """Delta mode should add normalized deltas to current positions."""
        from src.executor.action_converter import ActionConverter

        converter = ActionConverter()
        current = [0.0, -0.785, 0.0, -2.356, 0.0, 1.571]  # home
        delta = [0.1, 0.0, -0.1, 0.0, 0.1, 0.0]
        scale = 0.5  # scale factor for deltas

        result = converter.apply_delta(current, delta, scale=scale)
        assert len(result) == 6
        assert result[0] == pytest.approx(0.05, abs=0.01)  # 0.0 + 0.1 * 0.5
        # Should still be within joint limits
        for i, angle in enumerate(result):
            lo, hi = converter.joint_limits[i]
            assert lo <= angle <= hi


# =============================================================================
# ModelLoader Tests
# =============================================================================
class TestModelLoader:
    """Test VLA model factory."""

    def test_load_scripted(self):
        """Should load ScriptedPolicy."""
        from src.executor.models.model_loader import ModelLoader

        model = ModelLoader.load("scripted")
        assert model is not None
        action = model.predict(instruction="pick apple from shelf A")
        assert isinstance(action, RobotAction)
        assert len(action.joint_angles) == 6

    def test_load_unknown_raises(self):
        """Should raise for unknown model type."""
        from src.executor.models.model_loader import ModelLoader

        with pytest.raises(ValueError, match="Unknown model type"):
            ModelLoader.load("nonexistent_model")

    def test_available_models(self):
        """Should list available model types."""
        from src.executor.models.model_loader import ModelLoader

        models = ModelLoader.available_models()
        assert "scripted" in models
        assert "smolvla" in models


# =============================================================================
# VLANode Tests
# =============================================================================
class TestVLANode:
    """Test VLA inference node."""

    def test_create_with_scripted(self):
        """VLANode should create with scripted policy."""
        from src.executor.vla_node import VLANode

        node = VLANode(model_type="scripted")
        assert node is not None
        assert node.is_ready()

    def test_preprocess_image(self):
        """Image preprocessing should resize and normalize."""
        from src.executor.vla_node import VLANode

        node = VLANode(model_type="scripted")
        # Create a test image (640x480 RGB)
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        processed = node.preprocess_image(image)

        assert processed is not None
        # Should be a PIL Image or numpy array of appropriate size
        assert hasattr(processed, 'shape') or hasattr(processed, 'size')

    def test_predict_returns_robot_action(self):
        """Prediction should return a valid RobotAction."""
        from src.executor.vla_node import VLANode

        node = VLANode(model_type="scripted")
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        action = node.predict(image, instruction="pick apple from shelf A")

        assert isinstance(action, RobotAction)
        assert len(action.joint_angles) == 6
        assert 0.0 <= action.gripper <= 1.0

    def test_predict_without_image(self):
        """Scripted policy should work without image."""
        from src.executor.vla_node import VLANode

        node = VLANode(model_type="scripted")
        action = node.predict(image=None, instruction="pick apple from shelf A")

        assert isinstance(action, RobotAction)
        assert len(action.joint_angles) == 6

    def test_inference_time_tracking(self):
        """VLANode should track inference time."""
        from src.executor.vla_node import VLANode

        node = VLANode(model_type="scripted")
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        node.predict(image, instruction="pick apple")

        assert node.last_inference_time >= 0.0
        assert node.last_inference_time < 5.0  # scripted should be instant


# =============================================================================
# End-to-End Pipeline Tests
# =============================================================================
class TestVLAPipeline:
    """Test camera → VLA → robot action pipeline."""

    def test_camera_to_action_pipeline(self):
        """Full pipeline: mock camera → VLA → action converter → joint command."""
        from src.executor.action_converter import ActionConverter
        from src.executor.vla_node import VLANode
        from src.simulation.camera_capture import CameraCapture

        camera = CameraCapture(mode="mock")
        vla = VLANode(model_type="scripted")
        converter = ActionConverter()

        # Capture image
        image = camera.capture()
        assert image is not None

        # VLA inference
        action = vla.predict(image, instruction="pick apple from shelf A")
        assert isinstance(action, RobotAction)

        # Convert to joint command
        joint_positions, gripper_width = converter.convert(action)
        assert len(joint_positions) == 6
        for i, pos in enumerate(joint_positions):
            lo, hi = converter.joint_limits[i]
            assert lo <= pos <= hi

    def test_multi_step_trajectory(self):
        """Generate multi-step trajectory for pick-and-place."""
        from src.executor.vla_node import VLANode

        vla = VLANode(model_type="scripted")
        trajectory = vla.get_trajectory(instruction="pick apple from shelf A")

        assert len(trajectory) >= 3  # at least approach, grasp, place
        for action in trajectory:
            assert isinstance(action, RobotAction)
            assert len(action.joint_angles) == 6

    def test_pipeline_with_robot_controller(self):
        """Pipeline should integrate with RobotController."""
        from src.executor.action_converter import ActionConverter
        from src.executor.vla_node import VLANode
        from src.simulation.camera_capture import CameraCapture
        from src.simulation.robot_control import RobotController

        camera = CameraCapture(mode="mock")
        vla = VLANode(model_type="scripted")
        converter = ActionConverter()
        robot = RobotController(mode="mock")

        # Full loop
        image = camera.capture()
        action = vla.predict(image, instruction="pick apple from shelf A")
        joint_positions, gripper_width = converter.convert(action)

        # Execute on robot
        robot.set_joint_positions(joint_positions)
        robot.set_gripper(gripper_width)

        state = robot.get_joint_state()
        assert len(state.positions) == 6


class TestVLANodeSmolVLA:
    """Tests requiring actual SmolVLA model (slow, GPU)."""

    @pytest.mark.slow
    @pytest.mark.gpu
    def test_smolvla_loads_in_node(self):
        """VLANode should load SmolVLA on MPS."""
        from src.executor.vla_node import VLANode

        node = VLANode(model_type="smolvla")
        assert node.is_ready()

    @pytest.mark.slow
    @pytest.mark.gpu
    def test_smolvla_inference(self):
        """SmolVLA should produce action from image + instruction."""
        from src.executor.vla_node import VLANode

        node = VLANode(model_type="smolvla")
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        action = node.predict(image, instruction="pick the red apple from the shelf")

        assert isinstance(action, RobotAction)
        assert len(action.joint_angles) == 6
