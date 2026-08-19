# Autonomous Industrial Inspector (Digital Twin)

An industrial inspection and pick-and-place robotic system built using **ROS 2 Jazzy**, **Gazebo Harmonic**, and **MoveIt 2**.



## Key Features

* **Simulation:** Gazebo Harmonic Digital Twin environment
* **Motion Planning:** MoveIt 2 collision-free path execution
* **Perception:** OpenCV / PyTorch object classification pipeline
* **Architecture:** Modular ROS 2 packages with Docker support


## System Requirements

* **OS:** Ubuntu 24.04 LTS (Noble Numbat)
* **Middleware:** ROS 2 Jazzy Jalisco
* **Simulation:** Gazebo Harmonic
* **Motion Planning:** MoveIt 2


## Quick Start

### 1. Build the Workspace

cd ~/ros2_projects/autonomous-industrial-inspector
colcon build --symlink-install
source install/setup.bash

### 2. Launch the System

Launch the MoveIt 2 planning pipeline and MoveGroup node:

ros2 launch inspector_moveit_config moveit.launch.py


## Current Status & Development Roadmap

* [x] URDF & Digital Twin Gazebo Integration
* [x] MoveIt 2 Motion Planning Setup
* [ ] Perception Pipeline (OpenCV / PyTorch Integration)
* [ ] Automated Pick-and-Place Execution
* [ ] Dockerization


## Author

Nihara Randini - shniharard@gmail.com 
