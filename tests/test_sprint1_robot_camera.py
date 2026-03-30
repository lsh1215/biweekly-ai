"""Sprint 1: Robot control and camera tests."""

import numpy as np
import pytest

from src.common.types import RobotAction
from src.simulation.robot_control import RobotController
from src.simulation.camera_capture import CameraCapture


class TestRobotController:
    """Test robot arm control interface."""

    def test_home_position(self):
        rc = RobotController(mode="mock")
        rc.go_home()
        state = rc.get_joint_state()
        assert state.positions == RobotController.HOME_POSITION

    def test_set_joint_positions(self):
        rc = RobotController(mode="mock")
        target = [0.5, -0.3, 0.2, -1.8, 0.3, 1.2]
        rc.set_joint_positions(target)
        state = rc.get_joint_state()
        assert state.positions == target

    def test_joint_limits_clipping(self):
        rc = RobotController(mode="mock")
        # Set positions beyond limits
        extreme = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        rc.set_joint_positions(extreme)
        state = rc.get_joint_state()
        # Should be clipped to upper limits
        for pos, (lo, hi) in zip(state.positions, RobotController.JOINT_LIMITS):
            assert lo <= pos <= hi

    def test_wrong_joint_count_raises(self):
        rc = RobotController(mode="mock")
        with pytest.raises(ValueError):
            rc.set_joint_positions([0.0, 0.0])  # only 2 joints

    def test_gripper_open_close(self):
        rc = RobotController(mode="mock")
        rc.open_gripper()
        assert rc._current_gripper == RobotController.GRIPPER_MAX_WIDTH
        rc.close_gripper()
        assert rc._current_gripper == 0.0

    def test_execute_action(self):
        rc = RobotController(mode="mock")
        action = RobotAction(
            joint_angles=[0.5, -0.3, 0.2, -1.8, 0.3, 1.2],
            gripper=1.0,  # closed
        )
        rc.execute_action(action)
        state = rc.get_joint_state()
        assert state.positions == action.joint_angles
        assert rc._current_gripper == 0.0  # gripper=1.0 means closed

    def test_joint_state_has_names(self):
        rc = RobotController(mode="mock")
        state = rc.get_joint_state()
        assert len(state.names) == 6
        assert all(n.startswith("joint") for n in state.names)


class TestCameraCapture:
    """Test camera image capture."""

    def test_mock_capture_returns_image(self):
        cam = CameraCapture(mode="mock")
        img = cam.capture()
        assert img is not None
        assert img.shape == (480, 640, 3)
        assert img.dtype == np.uint8

    def test_mock_capture_has_content(self):
        cam = CameraCapture(mode="mock")
        img = cam.capture()
        # Not all same color (has objects drawn)
        assert img.std() > 10, "Image appears blank"

    def test_capture_and_save(self, tmp_path):
        cam = CameraCapture(mode="mock")
        path = tmp_path / "test.png"
        result = cam.capture_and_save(path)
        assert result is True
        assert path.exists()
        assert path.stat().st_size > 0

    def test_custom_resolution(self):
        cam = CameraCapture(mode="mock", width=320, height=240)
        img = cam.capture()
        assert img.shape == (240, 320, 3)
