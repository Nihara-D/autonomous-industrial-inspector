import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    pkg_description = get_package_share_directory('inspector_description')
    pkg_moveit_config = get_package_share_directory('inspector_moveit_config')

    # Robot Description (URDF)
    xacro_file = os.path.join(pkg_description, 'urdf', 'inspector_arm.urdf.xacro')
    robot_description_config = xacro.process_file(xacro_file)
    robot_description = {'robot_description': robot_description_config.toxml()}

    # Robot Description Semantic (SRDF)
    srdf_file = os.path.join(pkg_moveit_config, 'config', 'inspector_arm.srdf')
    with open(srdf_file, 'r') as f:
        semantic_config = f.read()
    robot_description_semantic = {'robot_description_semantic': semantic_config}

    # Kinematics config dict load කිරීම
    kinematics_yaml_path = os.path.join(pkg_moveit_config, 'config', 'kinematics.yaml')
    with open(kinematics_yaml_path, 'r') as f:
        kinematics_config = yaml.safe_load(f)
    robot_description_kinematics = {'robot_description_kinematics': kinematics_config}

    # MoveGroup Node setup
    move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
            {'publish_robot_description_semantic': True}
        ]
    )

    # Static TF Publisher (New Arguments format for Jazzy)
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_transform_publisher',
        output='log',
        arguments=['--x', '0', '--y', '0', '--z', '0', '--roll', '0', '--pitch', '0', '--yaw', '0', '--frame-id', 'world', '--child-frame-id', 'base_link']
    )

    # Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description]
    )

    return LaunchDescription([
        static_tf,
        robot_state_publisher,
        move_group_node
    ])
