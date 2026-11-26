"""Deprecated compatibility entry point: ArmPi Ultra plant.

The implementation lives in ``jcheng_simulation_robots``; this file keeps the
old command working:

    ros2 launch jcheng_simulation_bringup sim.launch.py backend:=mock

Prefer:

    ros2 launch jcheng_simulation_robots robot.launch.py robot:=armpi_ultra backend:=mock
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    engine = os.path.join(
        get_package_share_directory("jcheng_simulation_robots"),
        "launch",
        "robot.launch.py",
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "backend", default_value="mock", choices=["mock", "gz"]
            ),
            DeclareLaunchArgument("domain_id", default_value="43"),
            DeclareLaunchArgument("headless", default_value="true"),
            DeclareLaunchArgument("world", default_value=""),
            DeclareLaunchArgument("model_name", default_value=""),
            DeclareLaunchArgument("controller_manager", default_value=""),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(engine),
                launch_arguments={
                    "robot": "armpi_ultra",
                    "backend": LaunchConfiguration("backend"),
                    "domain_id": LaunchConfiguration("domain_id"),
                    "headless": LaunchConfiguration("headless"),
                    "world": LaunchConfiguration("world"),
                    "model_name": LaunchConfiguration("model_name"),
                    "controller_manager": LaunchConfiguration("controller_manager"),
                }.items(),
            ),
        ]
    )
