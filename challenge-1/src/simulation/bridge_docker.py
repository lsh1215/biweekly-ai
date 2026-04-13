"""ZMQ bridge running inside Docker container.

Publishes camera images from ROS2 to ZMQ (port 5555).
Subscribes to robot commands from ZMQ (port 5556) and publishes to ROS2.
"""

from __future__ import annotations

import json
import time
import struct
import threading

import zmq


class DockerBridge:
    """Bridge between ROS2 (inside Docker) and host (macOS) via ZMQ."""

    def __init__(self, pub_port: int = 5555, sub_port: int = 5556):
        self.context = zmq.Context()

        # PUB socket: send camera images to host
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://*:{pub_port}")

        # SUB socket: receive commands from host
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.bind(f"tcp://*:{sub_port}")
        self.sub_socket.subscribe(b"")

        self.running = False
        print(f"DockerBridge: PUB on :{pub_port}, SUB on :{sub_port}")

    def publish_image(self, image_data: bytes, width: int, height: int, timestamp: float) -> None:
        """Publish camera image over ZMQ."""
        header = json.dumps({
            "type": "camera_image",
            "width": width,
            "height": height,
            "timestamp": timestamp,
            "encoding": "rgb8",
        }).encode()

        self.pub_socket.send_multipart([b"camera", header, image_data])

    def publish_joint_state(self, joint_names: list[str], positions: list[float]) -> None:
        """Publish robot joint state over ZMQ."""
        msg = json.dumps({
            "type": "joint_state",
            "names": joint_names,
            "positions": positions,
            "timestamp": time.time(),
        }).encode()

        self.pub_socket.send_multipart([b"joint_state", msg])

    def receive_command(self, timeout: int = 100) -> dict | None:
        """Receive a robot command from host. Returns None on timeout."""
        if self.sub_socket.poll(timeout):
            frames = self.sub_socket.recv_multipart()
            if len(frames) >= 2:
                topic = frames[0].decode()
                data = json.loads(frames[1].decode())
                return {"topic": topic, **data}
        return None

    def start(self) -> None:
        """Start the bridge (blocking)."""
        self.running = True
        print("DockerBridge: Started")

        try:
            while self.running:
                cmd = self.receive_command(timeout=100)
                if cmd:
                    self._handle_command(cmd)
        except KeyboardInterrupt:
            print("DockerBridge: Shutting down")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the bridge."""
        self.running = False
        self.pub_socket.close()
        self.sub_socket.close()
        self.context.term()

    def _handle_command(self, cmd: dict) -> None:
        """Handle incoming command from host."""
        cmd_type = cmd.get("type", "unknown")

        if cmd_type == "joint_command":
            positions = cmd.get("positions", [])
            print(f"DockerBridge: Joint command received: {positions}")
            # TODO: Publish to ROS2 joint command topic

        elif cmd_type == "gripper_command":
            width = cmd.get("width", 0.04)
            print(f"DockerBridge: Gripper command: width={width}")
            # TODO: Publish to ROS2 gripper topic

        elif cmd_type == "capture_image":
            print("DockerBridge: Image capture requested")
            # TODO: Capture latest image from ROS2 and publish

        else:
            print(f"DockerBridge: Unknown command type: {cmd_type}")


def main():
    """Run the bridge as a standalone process."""
    bridge = DockerBridge()
    bridge.start()


if __name__ == "__main__":
    main()
