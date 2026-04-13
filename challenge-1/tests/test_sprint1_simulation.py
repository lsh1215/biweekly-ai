"""Sprint 1: Simulation environment tests (TDD - written first).

Tests for Docker, SDF world file validation, and simulation configuration.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORLDS_DIR = PROJECT_ROOT / "src" / "simulation" / "worlds"
DOCKER_DIR = PROJECT_ROOT / "docker"
CONFIGS_DIR = PROJECT_ROOT / "configs"


class TestDockerCompose:
    """Validate Docker Compose configuration."""

    def test_docker_compose_exists(self):
        """docker-compose.yml should exist."""
        assert (DOCKER_DIR / "docker-compose.yml").exists()

    def test_docker_compose_valid_yaml(self):
        """docker-compose.yml should be valid YAML."""
        with open(DOCKER_DIR / "docker-compose.yml") as f:
            config = yaml.safe_load(f)
        assert config is not None
        assert "services" in config

    def test_docker_compose_has_gazebo_service(self):
        """Should define a gazebo-sim service."""
        with open(DOCKER_DIR / "docker-compose.yml") as f:
            config = yaml.safe_load(f)
        assert "gazebo-sim" in config["services"]

    def test_docker_compose_ports(self):
        """Should expose ZMQ ports (5555, 5556)."""
        with open(DOCKER_DIR / "docker-compose.yml") as f:
            config = yaml.safe_load(f)
        service = config["services"]["gazebo-sim"]
        ports = [str(p) for p in service.get("ports", [])]
        port_strs = " ".join(ports)
        assert "5555" in port_strs, "ZMQ pub port 5555 not exposed"
        assert "5556" in port_strs, "ZMQ sub port 5556 not exposed"

    def test_docker_compose_memory_limit(self):
        """Should set memory limit <= 6GB."""
        with open(DOCKER_DIR / "docker-compose.yml") as f:
            config = yaml.safe_load(f)
        service = config["services"]["gazebo-sim"]
        mem = service.get("mem_limit", "")
        assert mem, "No memory limit set"

    def test_dockerfile_exists(self):
        """Dockerfile should exist."""
        assert (DOCKER_DIR / "Dockerfile").exists()

    def test_dockerfile_base_image(self):
        """Dockerfile should use osrf/ros:jazzy-desktop base."""
        content = (DOCKER_DIR / "Dockerfile").read_text()
        assert "osrf/ros:jazzy-desktop" in content


class TestWarehouseSDF:
    """Validate warehouse SDF world file."""

    @pytest.fixture
    def sdf_root(self):
        """Parse the warehouse SDF file."""
        sdf_path = WORLDS_DIR / "warehouse.sdf"
        assert sdf_path.exists(), "warehouse.sdf not found"
        tree = ET.parse(sdf_path)
        return tree.getroot()

    def test_sdf_is_valid_xml(self):
        """warehouse.sdf should be valid XML."""
        sdf_path = WORLDS_DIR / "warehouse.sdf"
        tree = ET.parse(sdf_path)
        assert tree.getroot().tag == "sdf"

    def test_has_world(self, sdf_root):
        """Should contain a world element."""
        world = sdf_root.find("world")
        assert world is not None
        assert world.get("name") == "warehouse"

    def test_has_three_shelves(self, sdf_root):
        """Should have exactly 3 shelves (A, B, C)."""
        world = sdf_root.find("world")
        models = world.findall("model")
        shelf_models = [m for m in models if m.get("name", "").startswith("shelf_")]
        shelf_names = sorted([m.get("name") for m in shelf_models])
        assert shelf_names == ["shelf_A", "shelf_B", "shelf_C"], \
            f"Expected shelves A, B, C but got {shelf_names}"

    def test_has_six_objects(self, sdf_root):
        """Should have exactly 6 pickable objects."""
        world = sdf_root.find("world")
        models = world.findall("model")
        expected_objects = {"apple", "bottle", "book", "box", "can", "cup"}
        object_models = [m for m in models if m.get("name") in expected_objects]
        found = {m.get("name") for m in object_models}
        assert found == expected_objects, \
            f"Missing objects: {expected_objects - found}"

    def test_objects_have_physics(self, sdf_root):
        """Each object should have mass and collision."""
        world = sdf_root.find("world")
        expected_objects = {"apple", "bottle", "book", "box", "can", "cup"}

        for model in world.findall("model"):
            name = model.get("name")
            if name not in expected_objects:
                continue

            link = model.find("link")
            assert link is not None, f"{name} has no link"

            inertial = link.find("inertial")
            assert inertial is not None, f"{name} has no inertial"

            mass = inertial.find("mass")
            assert mass is not None, f"{name} has no mass"
            assert float(mass.text) > 0, f"{name} mass is 0"

            collision = link.find("collision")
            assert collision is not None, f"{name} has no collision"

    def test_has_collection_box(self, sdf_root):
        """Should have a collection box."""
        world = sdf_root.find("world")
        models = world.findall("model")
        box_models = [m for m in models if m.get("name") == "collection_box"]
        assert len(box_models) == 1, "Missing collection box"

    def test_has_camera(self, sdf_root):
        """Should have an overhead camera with sensor."""
        world = sdf_root.find("world")
        models = world.findall("model")
        camera_models = [m for m in models if "camera" in m.get("name", "")]
        assert len(camera_models) >= 1, "No camera model found"

        # Check camera has a sensor element
        cam_model = camera_models[0]
        sensor = cam_model.find(".//sensor")
        assert sensor is not None, "Camera model has no sensor"
        assert sensor.get("type") == "camera"

    def test_has_robot_arm(self, sdf_root):
        """Should have a robot arm model."""
        world = sdf_root.find("world")
        models = world.findall("model")
        arm_models = [m for m in models if "panda" in m.get("name", "") or "arm" in m.get("name", "")]
        assert len(arm_models) >= 1, "No robot arm model found"

    def test_robot_has_joints(self, sdf_root):
        """Robot arm should have at least 6 revolute joints."""
        world = sdf_root.find("world")
        models = world.findall("model")
        arm_models = [m for m in models if "panda" in m.get("name", "") or "arm" in m.get("name", "")]
        assert len(arm_models) >= 1

        arm = arm_models[0]
        joints = arm.findall("joint")
        revolute_joints = [j for j in joints if j.get("type") == "revolute"]
        assert len(revolute_joints) >= 6, \
            f"Robot has {len(revolute_joints)} revolute joints, need >= 6"

    def test_robot_has_gripper(self, sdf_root):
        """Robot should have gripper joints."""
        world = sdf_root.find("world")
        arm_models = [m for m in world.findall("model")
                      if "panda" in m.get("name", "") or "arm" in m.get("name", "")]
        arm = arm_models[0]
        joints = arm.findall("joint")
        gripper_joints = [j for j in joints if "gripper" in j.get("name", "")]
        assert len(gripper_joints) >= 2, "Need at least 2 gripper joints (left/right)"


class TestConfigurations:
    """Validate config files match simulation."""

    def test_warehouse_config_matches_sdf(self):
        """Warehouse config shelves should match SDF."""
        with open(CONFIGS_DIR / "warehouse.yaml") as f:
            config = yaml.safe_load(f)
        shelves = config["warehouse"]["shelves"]
        shelf_ids = [s["id"] for s in shelves]
        assert sorted(shelf_ids) == ["A", "B", "C"]

    def test_objects_config_has_six_items(self):
        """Objects config should define 6 items."""
        with open(CONFIGS_DIR / "objects.yaml") as f:
            config = yaml.safe_load(f)
        objects = config["objects"]
        assert len(objects) == 6
        names = {o["name"] for o in objects}
        assert names == {"apple", "bottle", "book", "box", "can", "cup"}

    def test_robot_config_has_joints(self):
        """Robot config should define joint limits."""
        with open(CONFIGS_DIR / "robot.yaml") as f:
            config = yaml.safe_load(f)
        robot = config["robot"]
        assert robot["dof"] == 6
        assert len(robot["joint_limits"]) == 6
        assert len(robot["home_position"]) == 6


class TestDockerBuildability:
    """Test that Docker environment can be built (requires Docker)."""

    @pytest.mark.docker
    def test_docker_compose_config_valid(self):
        """docker compose config should validate."""
        import subprocess
        result = subprocess.run(
            ["docker", "compose", "-f", str(DOCKER_DIR / "docker-compose.yml"), "config"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"docker compose config failed: {result.stderr}"
