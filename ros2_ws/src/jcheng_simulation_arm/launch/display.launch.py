"""Deprecated compatibility entry point: Gate-2 arm RViz display.

Prefer ``ros2 launch jcheng_simulation_robots display.launch.py robot:=gate2_arm``.
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
        "display.launch.py",
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument("gui", default_value="false"),
            DeclareLaunchArgument("domain_id", default_value="43"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(engine),
                launch_arguments={
                    "robot": "gate2_arm",
                    "gui": LaunchConfiguration("gui"),
                    "domain_id": LaunchConfiguration("domain_id"),
                }.items(),
            ),
        ]
    )
