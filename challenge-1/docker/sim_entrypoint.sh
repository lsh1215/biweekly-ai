#!/bin/bash
set -e

# Source ROS2
source /opt/ros/jazzy/setup.bash

echo "=== Warehouse Picker Simulation ==="
echo "ROS2 Distro: $ROS_DISTRO"

# Start Gazebo with warehouse world (headless rendering for Docker)
if [ -f /ros2_ws/worlds/warehouse.sdf ]; then
    echo "Starting Gazebo with warehouse world..."
    gz sim -s -r /ros2_ws/worlds/warehouse.sdf &
    GZ_PID=$!

    # Wait for Gazebo to start
    sleep 5

    # Start ROS-Gazebo bridge for camera topic
    ros2 run ros_gz_bridge parameter_bridge \
        /camera@sensor_msgs/msg/Image@gz.msgs.Image \
        /camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo &

    # Start ZMQ bridge for host communication
    if [ -f /ros2_ws/bridge/bridge_docker.py ]; then
        python3 /ros2_ws/bridge/bridge_docker.py &
    fi

    echo "Simulation running. Gazebo PID: $GZ_PID"

    # Keep container running
    wait $GZ_PID
else
    echo "No warehouse.sdf found. Starting idle..."
    # Keep container alive for debugging
    tail -f /dev/null
fi
