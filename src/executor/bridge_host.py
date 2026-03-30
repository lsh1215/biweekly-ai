"""ZMQ bridge running on host (macOS).

Receives camera images from Docker via ZMQ (port 5555).
Sends robot commands to Docker via ZMQ (port 5556).
"""

from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
import zmq


class HostBridge:
    """Bridge between host (macOS VLA) and Docker (Gazebo) via ZMQ."""

    def __init__(self, docker_host: str = "localhost", pub_port: int = 5555, sub_port: int = 5556):
        self.context = zmq.Context()

        # SUB socket: receive images from Docker
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://{docker_host}:{pub_port}")
        self.sub_socket.subscribe(b"camera")
        self.sub_socket.subscribe(b"joint_state")

        # PUB socket: send commands to Docker
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.connect(f"tcp://{docker_host}:{sub_port}")

        self._last_image: np.ndarray | None = None
        self._last_joint_state: dict | None = None

        print(f"HostBridge: Connected to {docker_host} (SUB:{pub_port}, PUB:{sub_port})")

    def receive_image(self, timeout: int = 5000) -> np.ndarray | None:
        """Receive camera image from simulation.

        Returns:
            RGB numpy array (H, W, 3) or None on timeout.
        """
        if self.sub_socket.poll(timeout):
            frames = self.sub_socket.recv_multipart()
            if len(frames) >= 3 and frames[0] == b"camera":
                header = json.loads(frames[1].decode())
                width = header["width"]
                height = header["height"]
                image_data = frames[2]

                image = np.frombuffer(image_data, dtype=np.uint8).reshape(height, width, 3)
                self._last_image = image
                return image

        return self._last_image

    def receive_joint_state(self, timeout: int = 1000) -> dict | None:
        """Receive current joint state from simulation."""
        if self.sub_socket.poll(timeout):
            frames = self.sub_socket.recv_multipart()
            if len(frames) >= 2 and frames[0] == b"joint_state":
                data = json.loads(frames[1].decode())
                self._last_joint_state = data
                return data

        return self._last_joint_state

    def send_joint_command(self, positions: list[float]) -> None:
        """Send joint position command to simulation."""
        msg = json.dumps({
            "type": "joint_command",
            "positions": positions,
            "timestamp": time.time(),
        }).encode()

        self.pub_socket.send_multipart([b"command", msg])

    def send_gripper_command(self, width: float) -> None:
        """Send gripper command (0.0 = closed, 0.08 = open)."""
        msg = json.dumps({
            "type": "gripper_command",
            "width": width,
            "timestamp": time.time(),
        }).encode()

        self.pub_socket.send_multipart([b"command", msg])

    def request_image_capture(self) -> None:
        """Request the Docker bridge to capture and send current camera image."""
        msg = json.dumps({
            "type": "capture_image",
            "timestamp": time.time(),
        }).encode()

        self.pub_socket.send_multipart([b"command", msg])

    def save_image(self, path: str) -> bool:
        """Save the last received image to disk."""
        if self._last_image is None:
            return False

        from PIL import Image
        img = Image.fromarray(self._last_image)
        img.save(path)
        return True

    def close(self) -> None:
        """Close all sockets."""
        self.sub_socket.close()
        self.pub_socket.close()
        self.context.term()
