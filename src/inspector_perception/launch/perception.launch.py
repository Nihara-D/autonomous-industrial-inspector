import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg_bringup = get_package_share_directory('inspector_bringup')

    # simulation.launch.py already bridges /camera/image_raw and /camera/camera_info.
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bringup, 'launch', 'simulation.launch.py')))

    detector = Node(
        package='inspector_perception',
        executable='color_detector',
        name='color_detector',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    return LaunchDescription([simulation, TimerAction(period=5.0, actions=[detector])])
