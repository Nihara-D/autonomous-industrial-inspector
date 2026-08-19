import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder

def generate_launch_description():
    # inspector_description package එකේ urdf xacro path එක ලබා ගැනීම
    pkg_description = get_package_share_directory('inspector_description')
    urdf_path = os.path.join(pkg_description, 'urdf', 'inspector_arm.urdf.xacro')

    # MoveItConfigsBuilder මගින් Absolute Path භාවිතයෙන් Configurations Auto-load කිරීම
    moveit_config = (
        MoveItConfigsBuilder("inspector_arm", package_name="inspector_moveit_config")
        .robot_description(file_path=urdf_path)
        .robot_description_semantic(file_path="config/inspector_arm.srdf")
        .kinematics(file_path="config/kinematics.yaml")
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
    )

    # MoveGroup Node
    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[moveit_config.to_dict()]
    )

    # Static TF Publisher
    static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        arguments=['--x', '0', '--y', '0', '--z', '0', '--roll', '0', '--pitch', '0', '--yaw', '0', '--frame-id', 'world', '--child-frame-id', 'base_link']
    )

    # Robot State Publisher
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
