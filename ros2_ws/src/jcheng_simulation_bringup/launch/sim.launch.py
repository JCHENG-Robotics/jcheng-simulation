"""Launch the jcheng-simulation plant on domain 43.

Backends
--------
mock (default)
    A deterministic, ROS-only plant: joint setpoints on /sim/joint_command,
    joint states and a synthetic scan under /sim. No Gazebo, no devices.
gz
    Gazebo Sim (Harmonic) with the primitive ArmPi Ultra model, gz_ros2_control
    controllers, a GPU lidar and a camera. Headless by default.

Both backends are confined to ROS_DOMAIN_ID=43. The launch refuses any other
domain. No backend publishes a vendor topic or joins domains 0/41/42.
"""

from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _validate_domain(context) -> list:
    domain = LaunchConfiguration("domain_id").perform(context).strip()
    if domain != "43":
        raise RuntimeError(
            "jcheng-simulation is confined to ROS_DOMAIN_ID=43; "
            f"received domain_id:={domain!r}"
        )
    return []


def _mock_actions(context) -> list:
    share = get_package_share_directory("jcheng_simulation_bringup")
    urdf = os.path.join(share, "urdf", "jcheng_armpi_sim.urdf.xacro")
    return [
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            output="screen",
            parameters=[
                {
                    "robot_description": ParameterValue(
                        Command(["xacro ", urdf]), value_type=str
                    ),
                    "use_sim_time": False,
                }
            ],
        ),
        Node(
            package="jcheng_simulation_bringup",
            executable="mock_plant",
            name="jcheng_sim_mock_plant",
            output="screen",
            parameters=[
                {
                    "config_file": os.path.join(share, "config", "sim.yaml"),
                    "limits_file": os.path.join(share, "config", "joint_limits.yaml"),
                }
            ],
        ),
    ]


def _gz_actions(context) -> list:
    share = get_package_share_directory("jcheng_simulation_bringup")
    ros_gz_sim = get_package_share_directory("ros_gz_sim")

    world = LaunchConfiguration("world").perform(context)
    model_name = LaunchConfiguration("model_name").perform(context)
    controller_manager = LaunchConfiguration("controller_manager").perform(context)
    headless = LaunchConfiguration("headless").perform(context).strip().lower()
    headless_flag = "--headless-rendering" if headless in ("1", "true", "yes") else ""
    server_flag = "-s" if headless in ("1", "true", "yes") else ""
    gz_args = f"-r {server_flag} {headless_flag} -v 4 {world}"

    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(ros_gz_sim, "launch", "gz_sim.launch.py")
            ),
            launch_arguments={
                "gz_args": gz_args,
                "on_exit_shutdown": "true",
            }.items(),
        ),
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            output="screen",
            parameters=[
                {
                    "robot_description": ParameterValue(
                        Command(
                            [
                                "xacro ",
                                os.path.join(
                                    share, "urdf", "jcheng_armpi_sim.urdf.xacro"
                                ),
                            ]
                        ),
                        value_type=str,
                    ),
                    "use_sim_time": True,
                }
            ],
        ),
        TimerAction(
            period=3.0,
            actions=[
                Node(
                    package="ros_gz_sim",
                    executable="create",
                    name="spawn_jcheng_armpi_sim",
                    output="screen",
                    arguments=[
                        "-topic",
                        "robot_description",
                        "-name",
                        model_name,
                        "-z",
                        "0.0",
                    ],
                ),
                Node(
                    package="ros_gz_bridge",
                    executable="parameter_bridge",
                    name="ros_gz_bridge",
                    output="screen",
                    parameters=[
                        {
                            "config_file": os.path.join(
                                share, "config", "ros_gz_bridge.yaml"
                            )
                        }
                    ],
                ),
            ],
        ),
        TimerAction(
            period=8.0,
            actions=[
                ExecuteProcess(
                    cmd=[
                        "ros2",
                        "run",
                        "controller_manager",
                        "spawner",
                        "joint_state_broadcaster",
                        "-c",
                        controller_manager,
                        "--controller-manager-timeout",
                        "60",
                    ],
                    output="screen",
                )
            ],
        ),
        TimerAction(
            period=12.0,
            actions=[
                ExecuteProcess(
                    cmd=[
                        "ros2",
                        "run",
                        "controller_manager",
                        "spawner",
                        "arm_controller",
                        "gripper_controller",
                        "-c",
                        controller_manager,
                        "--controller-manager-timeout",
                        "60",
                        "--switch-timeout",
                        "60",
                    ],
                    output="screen",
                )
            ],
        ),
    ]


def generate_launch_description() -> LaunchDescription:
    share = get_package_share_directory("jcheng_simulation_bringup")
    mock_condition = IfCondition(
        PythonExpression(["'", LaunchConfiguration("backend"), "' == 'mock'"])
    )
    gz_condition = IfCondition(
        PythonExpression(["'", LaunchConfiguration("backend"), "' == 'gz'"])
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "backend",
                default_value="mock",
                choices=["mock", "gz"],
                description="Plant backend: deterministic mock or Gazebo Sim",
            ),
            DeclareLaunchArgument(
                "domain_id",
                default_value="43",
                description="ROS domain; only 43 is accepted",
            ),
            DeclareLaunchArgument(
                "world",
                default_value=os.path.join(share, "worlds", "jcheng_lab.sdf"),
                description="Gazebo world file (gz backend)",
            ),
            DeclareLaunchArgument(
                "model_name",
                default_value="jcheng_armpi_sim",
                description="Spawned Gazebo model name (gz backend)",
            ),
            DeclareLaunchArgument(
                "headless",
                default_value="true",
                description="Run Gazebo server only (gz backend)",
            ),
            DeclareLaunchArgument(
                "controller_manager",
                default_value="/sim/controller_manager",
                description="controller_manager node name (gz backend)",
            ),
            SetEnvironmentVariable("ROS_DOMAIN_ID", LaunchConfiguration("domain_id")),
            SetEnvironmentVariable("GZ_PARTITION", "jcheng-sim"),
            OpaqueFunction(function=_validate_domain),
            OpaqueFunction(function=_mock_actions, condition=mock_condition),
            OpaqueFunction(function=_gz_actions, condition=gz_condition),
        ]
    )
