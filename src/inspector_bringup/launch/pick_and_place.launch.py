"""Full autonomous pick-and-place demo: Gazebo + MoveIt + detector + pick-place node."""
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

    detector = Node(
        package='inspector_perception',
        executable='color_detector',
        name='color_detector',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    pick_place = Node(
        package='inspector_pick_place',
        executable='pick_place_node',
        name='pick_place_node',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'pick_order': LaunchConfiguration('pick_order'),
            'start_delay': 5.0,
        }],
    )

    delayed = TimerAction(period=10.0, actions=[detector, pick_place])

    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument(
            'pick_order', default_value='red,green,blue',
            description='Comma separated colours to pick, in order'),
        full_system,
        delayed,
    ])
