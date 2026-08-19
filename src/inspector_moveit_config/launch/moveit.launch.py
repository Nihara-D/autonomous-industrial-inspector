import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    pkg_description = get_package_share_directory('inspector_description')
    pkg_moveit_config = get_package_share_directory('inspector_moveit_config')

    # Robot Description
    xacro_file = os.path.join(pkg_description, 'urdf', 'inspector_arm.urdf.xacro')
    robot_description = {'robot_description': xacro.process_file(xacro_file).toxml()}

    # SRDF
    srdf_file = os.path.join(pkg_moveit_config, 'config', 'inspector_arm.srdf')
    with open(srdf_file, 'r') as f:
        robot_description_semantic = {'robot_description_semantic': f.read()}

    # Kinematics
    kinematics_yaml_path = os.path.join(pkg_moveit_config, 'config', 'kinematics.yaml')
    with open(kinematics_yaml_path, 'r') as f:
        robot_description_kinematics = {'robot_description_kinematics': yaml.safe_load(f)}

    # OMPL Pipeline
    ompl_yaml_path = os.path.join(pkg_moveit_config, 'config', 'ompl_planning.yaml')
    with open(ompl_yaml_path, 'r') as f:
        ompl_config = yaml.safe_load(f)
    
    ompl_pipeline_config = {
        'planning_pipelines': ['ompl'],
        'ompl': ompl_config
    }

    # MoveGroup Node
    move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
            ompl_pipeline_config,
            {'publish_robot_description_semantic': True}
        ]
    )

    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['--x', '0', '--y', '0', '--z', '0', '--roll', '0', '--pitch', '0', '--yaw', '0', '--frame-id', 'world', '--child-frame-id', 'base_link']
    )

    return LaunchDescription([static_tf, move_group_node])
