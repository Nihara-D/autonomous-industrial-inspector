import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder

def generate_launch_description():
    pkg_moveit = get_package_share_directory('inspector_moveit_config')
    pkg_description = get_package_share_directory('inspector_description')
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

    ompl_yaml_path = os.path.join(pkg_moveit, 'config', 'ompl_planning.yaml')
    with open(ompl_yaml_path, 'r') as f:
        ompl_yaml = yaml.safe_load(f)

    moveit_params = moveit_config.to_dict()
    moveit_params.update({
        'planning_pipelines': ['ompl'],
        'default_planning_pipeline': 'ompl',
        'ompl': ompl_yaml
    })

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[moveit_params]
    )

    static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        arguments=['--x', '0', '--y', '0', '--z', '0', '--roll', '0', '--pitch', '0', '--yaw', '0', '--frame-id', 'world', '--child-frame-id', 'base_link']
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[moveit_config.robot_description]
    )

    return LaunchDescription([
        static_tf,
        robot_state_publisher,
        move_group_node
    ])
