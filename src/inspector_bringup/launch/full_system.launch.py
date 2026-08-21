import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    pkg_bringup = get_package_share_directory('inspector_bringup')
    pkg_description = get_package_share_directory('inspector_description')

    # 1. Bring up Gazebo Harmonic + robot spawn + ros2_control controllers
    #    (joint_state_broadcaster, arm_controller) via the existing
    #    simulation.launch.py, unchanged.
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bringup, 'launch', 'simulation.launch.py')
        )
    )

    # 2. Build the MoveIt config the same way moveit.launch.py /
    #    moveit_rviz.launch.py already do, so move_group and RViz see the
    #    identical robot description, SRDF, kinematics, and controllers.
    urdf_path = os.path.join(pkg_description, 'urdf', 'inspector_arm.urdf.xacro')
    moveit_config = (
        MoveItConfigsBuilder("inspector_arm", package_name="inspector_moveit_config")
        .robot_description(file_path=urdf_path)
        .robot_description_semantic(file_path="config/inspector_arm.srdf")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .joint_limits(file_path="config/joint_limits.yaml")
        .pilz_cartesian_limits(file_path="config/pilz_cartesian_limits.yaml")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(
            pipelines=["ompl"],
            default_planning_pipeline="ompl"
        )
        .to_moveit_configs()
    )

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {'planning_pipelines': ['ompl']},
            {'default_planning_pipeline': 'ompl'},
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
            moveit_config.planning_pipelines,
            moveit_config.robot_description_kinematics,
        ],
    )

    # 3. Gazebo, the robot spawn, and the controller spawners all need a
    #    few seconds to come up before move_group/RViz should attach to
    #    them. A fixed delay is a simple, known limitation here -- swap
    #    this for an OnProcessExit/OnProcessStart event handler chained
    #    off the controller spawners if this proves flaky on slower
    #    machines.
    delayed_moveit = TimerAction(
        period=8.0,
        actions=[move_group_node, rviz_node]
    )

    return LaunchDescription([
        simulation,
        delayed_moveit
    ])
