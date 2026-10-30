#!/bin/bash
set -e
source /opt/ros/${ROS_DISTRO}/setup.bash
source ${WS}/install/setup.bash
exec "$@"
