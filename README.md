# Autonomous Industrial Inspector (Digital Twin)

An industrial inspection and pick-and-place robotic system built using **ROS 2 Jazzy**, **Gazebo Harmonic**, and **MoveIt 2**.

## Key Features

* **Simulation:** Gazebo Harmonic digital twin of a 4-DOF industrial arm
* **Control:** ros2_control + gz_ros2_control hardware interface, position-controlled joint trajectory controller
* **Motion Planning:** MoveIt 2 (OMPL) collision-free path planning and execution
* **Architecture:** Modular ROS 2 packages (`inspector_description`, `inspector_bringup`, `inspector_moveit_config`)

## Screenshots

![Gazebo simulation](docs/screenshots/gazebo.png)
![RViz motion planning](docs/screenshots/rviz_planning.png)

## System Requirements

* **OS:** Ubuntu 24.04 LTS (Noble Numbat)
* **Middleware:** ROS 2 Jazzy Jalisco
* **Simulation:** Gazebo Harmonic
* **Motion Planning:** MoveIt 2

## Quick Start

### 1. Build the workspace

```bash
cd ~/ros2_projects/autonomous-industrial-inspector
colcon build --symlink-install
source install/setup.bash
```

### 2. Launch the full system (Gazebo + ros2_control + MoveIt 2 + RViz)

```bash
ros2 launch inspector_bringup full_system.launch.py
```

This brings up Gazebo Harmonic with the robot spawned, `joint_state_broadcaster` and `arm_controller` active, then `move_group` and RViz with the MotionPlanning panel ready to plan and execute trajectories.

### 3. Gazebo-only bringup (no MoveIt)

```bash
ros2 launch inspector_bringup simulation.launch.py
```

## Current Status & Development Roadmap

* [x] URDF (4-DOF arm) & Gazebo Harmonic digital twin
* [x] ros2_control hardware interface, joint_state_broadcaster + arm_controller
* [x] MoveIt 2 motion planning (OMPL) — plan and execute via RViz
* [ ] Inspection environment (objects/shelving in Gazebo world)
* [ ] Perception pipeline (camera + OpenCV / PyTorch object classification)
* [ ] Automated pick-and-place execution
* [ ] Dockerization

## Author

Nihara Randini - shniharard@gmail.com
