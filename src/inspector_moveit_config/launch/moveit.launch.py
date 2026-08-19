import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    pkg_description = get_package_share_directory('inspector_description')
    pkg_moveit_config = get_package_share_directory('inspector_moveit_config')

    # 1. Robot Description (URDF)
    xacro_file = os.path.join(pkg_description, 'urdf', 'inspector_arm.urdf.xacro')
    robot_description = {'robot_description': xacro.process_file(xacro_file).toxml()}

    # 2. SRDF
    srdf_file = os.path.join(pkg_moveit_config, 'config', 'inspector_arm.srdf')
    with open(srdf_file, 'r') as f:
        robot_description_semantic = {'robot_description_semantic': f.read()}

    # 3. Kinematics
    kinematics_yaml_path = os.path.join(pkg_moveit_config, 'config', 'kinematics.yaml')
    with open(kinematics_yaml_path, 'r') as f:
        robot_description_kinematics = {'robot_description_kinematics': yaml.safe_load(f)}

    # 4. OMPL Planning Pipeline (Direct Python Dictionary Definition)
    ompl_planning_pipeline_config = {
        'planning_pipelines': ['ompl'],
        'default_planning_pipeline': 'ompl',
        'ompl': {
            'planning_plugin': 'ompl_interface/OMPLPlanner',
            'request_adapters': [
                'default_planner_request_adapters/AddTimeParameterization',
                'default_planner_request_adapters/FixWorkspaceBounds',
                'default_planner_request_adapters/FixStartStateBounds',
                'default_planner_request_adapters/FixInvalidJointStates',
                'default_planner_request_adapters/FixSeekingStart',
            ],
            'start_state_max_bounds_error': 0.1,
        },
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
            ompl_planning_pipeline_config,
            {'publish_robot_description_semantic': True}
        ]
    )

    # Static TF Publisher
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
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
