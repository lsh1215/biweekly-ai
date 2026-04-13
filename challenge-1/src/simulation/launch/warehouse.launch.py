"""ROS2 launch file for warehouse simulation.

Launches Gazebo with warehouse world, spawns robot, and starts bridges.
Usage: ros2 launch warehouse.launch.py
"""

import os
from pathlib import Path

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    # Paths
    worlds_dir = os.environ.get("GZ_WORLDS_DIR", "/ros2_ws/worlds")
    world_file = os.path.join(worlds_dir, "warehouse.sdf")

    # Launch arguments
    headless_arg = DeclareLaunchArgument(
        "headless",
        default_value="true",
        description="Run Gazebo headless (no GUI)",
    )

    gz_verbose_arg = DeclareLaunchArgument(
        "gz_verbose",
        default_value="1",
        description="Gazebo verbosity level",
    )

    # Set Gazebo resource path for models
    set_gz_resource = SetEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=os.environ.get("GZ_SIM_RESOURCE_PATH", "/ros2_ws/models"),
    )

    # Start Gazebo simulator (server only for headless)
    gz_sim = ExecuteProcess(
        cmd=[
            "gz", "sim",
            "-s",  # server only (headless)
            "-r",  # run immediately
            "--verbose", LaunchConfiguration("gz_verbose"),
            world_file,
        ],
        output="screen",
    )

    # ROS-Gazebo bridge: camera images
    camera_bridge = ExecuteProcess(
        cmd=[
            "ros2", "run", "ros_gz_bridge", "parameter_bridge",
            "/camera@sensor_msgs/msg/Image@gz.msgs.Image",
            "/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo",
        ],
        output="screen",
    )

    # ROS-Gazebo bridge: joint states
    joint_state_bridge = ExecuteProcess(
        cmd=[
            "ros2", "run", "ros_gz_bridge", "parameter_bridge",
            "/world/warehouse/model/panda_arm/joint_state@sensor_msgs/msg/JointState@gz.msgs.Model",
        ],
        output="screen",
    )

    return LaunchDescription([
        headless_arg,
        gz_verbose_arg,
        set_gz_resource,
        gz_sim,
        camera_bridge,
        joint_state_bridge,
    ])
