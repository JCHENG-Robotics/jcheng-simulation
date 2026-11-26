"""RViz/TF-only display of any catalog robot. No Gazebo, no controllers.

    ros2 launch jcheng_simulation_robots display.launch.py robot:=armpi_ultra
    ros2 launch jcheng_simulation_robots display.launch.py robot:=gate2_arm gui:=true

The launch stays on domain 43 so a simulated robot TF never appears in a robot
graph. ``gui:=true`` adds ``joint_state_publisher_gui`` and ``rviz2``.
"""

from __future__ import annotations

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    LogInfo,
    OpaqueFunction,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import xacro

from jcheng_simulation_robots.model import ensure_inertials
from jcheng_simulation_robots.profile import ProfileError, catalog, load_profile


def _validate_domain(context) -> list:
    domain = LaunchConfiguration("domain_id").perform(context).strip()
    if domain != "43":
        raise RuntimeError(
            "the simulation display is confined to ROS_DOMAIN_ID=43; "
            f"received domain_id:={domain!r}"
        )
    return []


def _launch_setup(context, *unused):
    share = Path(get_package_share_directory("jcheng_simulation_robots"))
    robots_root = share / "robots"
    robot_id = LaunchConfiguration("robot").perform(context).strip()
    if not robot_id:
        raise RuntimeError(f"robot:= is required; available: {catalog(robots_root)}")
    profile_path = robots_root / robot_id / "robot.yaml"
    if not profile_path.is_file():
        raise RuntimeError(f"unknown robot {robot_id!r}; available: {catalog(robots_root)}")
    try:
        profile = load_profile(profile_path)
    except ProfileError as exc:
        raise RuntimeError(f"invalid robot profile {profile_path}: {exc}") from exc
    if not profile.model_available or profile.urdf is None:
        missing = ", ".join(profile.missing_assets) or "model.urdf"
        raise RuntimeError(
            f"robot {robot_id!r} needs external assets ({missing}); "
            "see docs/MULTI_ROBOT.md and docs/robots/"
        )
    if profile.asset_prefix is not None:
        current = os.environ.get("AMENT_PREFIX_PATH", "")
        os.environ["AMENT_PREFIX_PATH"] = (
            f"{profile.asset_prefix}:{current}" if current else str(profile.asset_prefix)
        )
    try:
        xml = xacro.process_file(str(profile.urdf)).toxml()
    except Exception as exc:  # xacro raises several unrelated types
        raise RuntimeError(f"cannot build the display for {robot_id!r}: {exc}") from exc
    description, inserted = ensure_inertials(xml)

    actions = [
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            output="screen",
            parameters=[
                {
                    "robot_description": ParameterValue(description, value_type=str),
                    "use_sim_time": False,
                }
            ],
        ),
        Node(
            package="joint_state_publisher_gui",
            executable="joint_state_publisher_gui",
            output="screen",
            condition=IfCondition(LaunchConfiguration("gui")),
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            output="screen",
            condition=IfCondition(LaunchConfiguration("gui")),
        ),
    ]
    if inserted:
        actions.insert(
            0,
            LogInfo(
                msg=(
                    "inertial placeholders inserted for geometry-less URDF links: "
                    f"{list(inserted)}"
                )
            ),
        )
    return actions


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "robot",
                description="Robot id from the catalog (robots/<id>/robot.yaml)",
            ),
            DeclareLaunchArgument(
                "gui",
                default_value="false",
                description="Start joint_state_publisher_gui and rviz2",
            ),
            DeclareLaunchArgument(
                "domain_id",
                default_value="43",
                description="ROS domain; only 43 is accepted",
            ),
            SetEnvironmentVariable("ROS_DOMAIN_ID", LaunchConfiguration("domain_id")),
            OpaqueFunction(function=_validate_domain),
            OpaqueFunction(function=_launch_setup),
        ]
    )
