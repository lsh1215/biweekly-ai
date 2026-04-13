FROM osrf/ros:jazzy-desktop

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install Gazebo Harmonic + ROS2 control packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-ros-gz \
    ros-jazzy-ros2-control \
    ros-jazzy-ros2-controllers \
    ros-jazzy-xacro \
    ros-jazzy-joint-state-publisher \
    ros-jazzy-robot-state-publisher \
    python3-pip \
    python3-zmq \
    mesa-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python ZMQ for bridge
RUN pip3 install --break-system-packages pyzmq pyyaml pillow

# Create workspace
WORKDIR /ros2_ws
RUN mkdir -p src/warehouse_sim

# Copy simulation files
COPY sim_entrypoint.sh /ros2_ws/sim_entrypoint.sh
RUN chmod +x /ros2_ws/sim_entrypoint.sh

# Source ROS2 setup
RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc

# Ports: ZMQ pub (5555), ZMQ sub (5556), Gazebo (11345)
EXPOSE 5555 5556 11345

ENTRYPOINT ["/ros2_ws/sim_entrypoint.sh"]
