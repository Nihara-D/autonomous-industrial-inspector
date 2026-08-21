import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    pkg_description = get_package_share_directory('inspector_description')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # 1. Process Xacro
    xacro_file = os.path.join(pkg_description, 'urdf', 'inspector_arm.urdf.xacro')
    robot_desc = xacro.process_file(xacro_file).toxml()

    # 2. Start Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc}]
    )

    # 3. Launch Gazebo Harmonic (gz_sim) with empty world
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': '-r empty.sdf'}.items(),
    )

    # 4. Spawn Robot in Gazebo using ros_gz_sim bridge
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'industrial_inspector',
            '-string', robot_desc,
            '-x', '0.0', '-y', '0.0', '-z', '0.0'
        ],
        output='screen'
    )

    # 5. Spawn ros2_control controllers (loaded via controller_manager once the
    #    robot exists in Gazebo and the gz_ros2_control plugin has started).
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        output='screen'
    )

    arm_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_controller'],
        output='screen'
    )

    # Spawn controllers only after spawn_robot has finished, so the
    # controller_manager (started by the gz_ros2_control plugin) is up first.
    delayed_controller_spawners = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_robot,
            on_exit=[joint_state_broadcaster_spawner, arm_controller_spawner],
        )
    )

    return LaunchDescription([
        robot_state_publisher,
        gazebo,
        spawn_robot,
        delayed_controller_spawners
    ])
