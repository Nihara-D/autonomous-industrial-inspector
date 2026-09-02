import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)
    try:
        with open(absolute_file_path, 'r') as f:
            return yaml.safe_load(f)
    except OSError:
        return None


def generate_launch_description():
    pkg_bringup = get_package_share_directory('inspector_bringup')
    pkg_description = get_package_share_directory('inspector_description')

    # 1. Bring up Gazebo Harmonic + robot spawn + ros2_control controllers
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bringup, 'launch', 'simulation.launch.py')
        )
    )

    # 2. Build the MoveIt config
    urdf_path = os.path.join(pkg_description, 'urdf', 'inspector_arm.urdf.xacro')
    moveit_config = (
        MoveItConfigsBuilder("inspector_arm", package_name="inspector_moveit_config")
        .robot_description(file_path=urdf_path)
        .robot_description_semantic(file_path="config/inspector_arm.srdf")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .joint_limits(file_path="config/joint_limits.yaml")
        .pilz_cartesian_limits(file_path="config/pilz_cartesian_limits.yaml")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .to_moveit_configs()
    )

    # Load the OMPL pipeline yaml directly and force it into the "ompl"
    # parameter namespace move_group actually looks under -- sidesteps a
    # version-specific quirk in MoveItConfigsBuilder's own pipeline loader.
    ompl_planning_yaml = load_yaml(
        "inspector_moveit_config", "config/ompl_planning.yaml"
    )

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {
                "planning_pipelines": ["ompl"],
                "default_planning_pipeline": "ompl",
                "ompl": ompl_planning_yaml,
            },
        ]
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            {
                "planning_pipelines": ["ompl"],
                "default_planning_pipeline": "ompl",
                "ompl": ompl_planning_yaml,
            },
        ],
    )

    # 3. Delay move_group/RViz so Gazebo + controllers are up first.
    delayed_moveit = TimerAction(
        period=8.0,
        actions=[move_group_node, rviz_node]
    )

    return LaunchDescription([
        simulation,
        delayed_moveit
    ])
