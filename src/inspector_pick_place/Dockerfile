FROM osrf/ros:jazzy-desktop-full

ENV DEBIAN_FRONTEND=noninteractive \
    ROS_DISTRO=jazzy \
    WS=/ws

RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-jazzy-ros-gz \
        ros-jazzy-gz-ros2-control \
        ros-jazzy-ros2-control \
        ros-jazzy-ros2-controllers \
        ros-jazzy-moveit \
        ros-jazzy-moveit-configs-utils \
        ros-jazzy-xacro \
        ros-jazzy-joint-state-publisher \
        ros-jazzy-joint-state-publisher-gui \
        python3-colcon-common-extensions \
        python3-numpy \
        python3-opencv \
        python3-pytest \
        mesa-utils \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${WS}
COPY src ${WS}/src

RUN . /opt/ros/${ROS_DISTRO}/setup.sh \
    && colcon build --symlink-install --event-handlers console_cohesion+

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["ros2", "launch", "inspector_bringup", "pick_and_place.launch.py"]
