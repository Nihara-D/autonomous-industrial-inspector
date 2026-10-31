"""Everything the operator web app needs: simulation, MoveIt, camera pipeline,
rosbridge (WebSocket on :9090) and the task manager that takes commands from the app."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_bringup = get_package_share_directory('inspector_bringup')

    full_system = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bringup, 'launch', 'full_system.launch.py')),
        launch_arguments={'rviz': LaunchConfiguration('rviz')}.items(),
    )

    rosbridge = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
        name='rosbridge_websocket',
        output='screen',
        parameters=[{'port': 9090}],
    )

    detector = Node(
        package='inspector_perception', executable='color_detector',
        name='color_detector', output='screen',
        parameters=[{'use_sim_time': True}],
    )

    camera_jpeg = Node(
        package='inspector_perception', executable='camera_jpeg',
        name='camera_jpeg', output='screen',
        parameters=[{'use_sim_time': True}],
    )

    task_manager = Node(
        package='inspector_pick_place', executable='task_manager',
        name='pick_place_node', output='screen',
        parameters=[{'use_sim_time': True, 'start_delay': 5.0}],
    )

    delayed = TimerAction(period=10.0, actions=[detector, camera_jpeg, task_manager])

    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='false',
                              description='Also open RViz (off by default for the app)'),
        full_system,
        rosbridge,
        delayed,
    ])
