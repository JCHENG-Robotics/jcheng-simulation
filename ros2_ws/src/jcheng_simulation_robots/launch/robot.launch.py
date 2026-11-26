"""Launch any catalog robot plant on domain 43.

    ros2 launch jcheng_simulation_robots robot.launch.py robot:=armpi_ultra backend:=mock
    ros2 launch jcheng_simulation_robots robot.launch.py robot:=gate2_arm backend:=gz

Backends
--------
mock
    Deterministic, ROS-only plant: joint setpoints on the profile's
    ``joint_command`` topic, joint states and (when declared) a synthetic scan.
gz
    Gazebo Harmonic with the profile's world, URDF, controllers and
    ``ros_gz_bridge`` sensors. Startup is fail-closed: ``spawn`` then each
    controller in ``startup_order``; a stage starts only if the previous process
    exited 0, and every stage has its own wall deadline.

Both backends are confined to ``ROS_DOMAIN_ID=43``; the launch refuses any other
domain. No plant publishes a vendor topic or joins domains 0/41/42.
"""

from __future__ import annotations

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import xacro

from jcheng_simulation_robots.controller_config import ControllerConfigError
from jcheng_simulation_robots.model import ensure_inertials, ensure_joint_dynamics
from jcheng_simulation_robots.profile import Profile, ProfileError, catalog, load_profile

SPAWN_DELAY_SECONDS = 3.0
DEFAULT_STARTUP_TIMEOUT_S = 60.0


def _validate_domain(context) -> list:
    domain = LaunchConfiguration("domain_id").perform(context).strip()
    if domain != "43":
        raise RuntimeError(
            "the simulation plant is confined to ROS_DOMAIN_ID=43; "
            f"received domain_id:={domain!r}"
        )
    return []


def _shutdown(stage, reason):
    # A zero exit during teardown is a normal stop, not a launch failure.
    label = "plant stop" if reason.endswith("returncode=0") else "plant launch failure"
    return [
        LogInfo(msg=f"{label}: stage={stage}; {reason}"),
        EmitEvent(event=Shutdown(reason=f"{stage}: {reason}")),
    ]


def _start_stage(stage, action, timeout_s):
    """Start a stage and its deadline in the same launch event."""
    return [action, _watchdog(stage, timeout_s)]


def _after_success(stage, next_stage=None, timeout_s=DEFAULT_STARTUP_TIMEOUT_S):
    def callback(event, context):
        if event.returncode == 0:
            context.launch_configurations[f"robot_startup_{stage}_completed"] = "true"
            return (
                _start_stage(next_stage[0], next_stage[1], timeout_s)
                if next_stage is not None
                else []
            )
        return _shutdown(
            stage, f"command={event.process_name}; returncode={event.returncode}"
        )

    return callback


def _watchdog(stage, timeout_s):
    def callback(context):
        if context.launch_configurations.get(f"robot_startup_{stage}_completed") == "true":
            return []
        return _shutdown(stage, f"wall deadline exceeded ({timeout_s}s)")

    return TimerAction(
        period=float(timeout_s), actions=[OpaqueFunction(function=callback)]
    )


def _resolve_override(value: str, profile: Profile, label: str) -> Path | None:
    if not value:
        return None
    path = Path(os.path.expandvars(os.path.expanduser(value)))
    if not path.is_absolute():
        path = profile.root / path
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(f"{label} does not resolve: {path}: {exc}") from exc
    if not resolved.is_file():
        raise RuntimeError(f"{label} is not a regular file: {resolved}")
    return resolved


def _robot_description(
    profile: Profile, controller_yaml: Path | None
) -> tuple[str, tuple[str, ...]]:
    if profile.urdf is None:
        raise RuntimeError(f"robot {profile.robot_id!r} has no resolved URDF")
    mappings = {}
    if profile.controller_arg and controller_yaml is not None:
        mappings[profile.controller_arg] = str(controller_yaml)
    try:
        xml = xacro.process_file(str(profile.urdf), mappings=mappings).toxml()
    except Exception as exc:  # xacro raises several unrelated types
        raise RuntimeError(f"xacro failed for {profile.urdf}: {exc}") from exc
    xml, inserted = ensure_inertials(xml)
    notes: list[str] = []
    if inserted:
        notes.append(f"inertial placeholders for {list(inserted)}")
    if profile.joint_damping is not None:
        xml, damped = ensure_joint_dynamics(xml, profile.joint_damping)
        if damped:
            notes.append(f"joint damping {profile.joint_damping} for {list(damped)}")
    return xml, tuple(notes)


def _require_model(profile: Profile) -> None:
    if profile.model_available and profile.urdf is not None:
        return
    missing = ", ".join(profile.missing_assets) or "model.urdf"
    raise RuntimeError(
        f"robot {profile.robot_id!r} needs external assets ({missing}); "
        "see docs/MULTI_ROBOT.md and docs/robots/"
    )


def _apply_asset_prefix(profile: Profile) -> None:
    """Prepend the profile's asset prefix so $(find ...) and meshes resolve."""

    if profile.asset_prefix is None:
        return
    current = os.environ.get("AMENT_PREFIX_PATH", "")
    os.environ["AMENT_PREFIX_PATH"] = (
        f"{profile.asset_prefix}:{current}" if current else str(profile.asset_prefix)
    )
    share = profile.asset_prefix / "share"
    if share.is_dir():
        current_gz = os.environ.get("GZ_SIM_RESOURCE_PATH", "")
        os.environ["GZ_SIM_RESOURCE_PATH"] = (
            f"{share}:{current_gz}" if current_gz else str(share)
        )


def _load_robot(context) -> Profile:
    share = get_package_share_directory("jcheng_simulation_robots")
    robots_root = Path(share) / "robots"
    robot_id = LaunchConfiguration("robot").perform(context).strip()
    if not robot_id:
        raise RuntimeError(
            f"robot:= is required; available: {catalog(robots_root)}"
        )
    profile_path = robots_root / robot_id / "robot.yaml"
    if not profile_path.is_file():
        raise RuntimeError(
            f"unknown robot {robot_id!r}; available: {catalog(robots_root)}"
        )
    try:
        return load_profile(profile_path)
    except (ProfileError, ControllerConfigError) as exc:
        raise RuntimeError(f"invalid robot profile {profile_path}: {exc}") from exc


def _mock_actions(context, profile: Profile, description: str) -> list:
    share = get_package_share_directory("jcheng_simulation_robots")
    profile_file = os.path.join(share, "robots", profile.robot_id, "robot.yaml")
    return [
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
            package="jcheng_simulation_robots",
            executable="mock_plant",
            name="jcheng_sim_mock_plant",
            output="screen",
            parameters=[{"profile_file": profile_file}],
        ),
    ]


def _gz_actions(context, profile: Profile, description: str, selection) -> list:
    share = get_package_share_directory("jcheng_simulation_robots")
    ros_gz_sim = get_package_share_directory("ros_gz_sim")

    world = _resolve_override(
        LaunchConfiguration("world").perform(context).strip(), profile, "world"
    ) or profile.world
    model_name = (
        LaunchConfiguration("model_name").perform(context).strip() or profile.model_name
    )
    manager = (
        LaunchConfiguration("controller_manager").perform(context).strip()
        or profile.manager_node
    )
    headless = LaunchConfiguration("headless").perform(context).strip().lower()
    headless_flag = "--headless-rendering" if headless in ("1", "true", "yes") else ""
    server_flag = "-s" if headless in ("1", "true", "yes") else ""
    gz_args = f"-r {server_flag} {headless_flag} -v 4 {world}"

    timeout_value = LaunchConfiguration("startup_timeout").perform(context).strip()
    timeout_s = float(timeout_value) if timeout_value else profile.startup_timeout_s

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[
            {
                "robot_description": ParameterValue(description, value_type=str),
                "use_sim_time": True,
            }
        ],
    )
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={"gz_args": gz_args, "on_exit_shutdown": "true"}.items(),
    )
    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        output="screen",
    )
    truth = Node(
        package="jcheng_simulation_robots",
        executable="truth_publisher",
        name="jcheng_sim_truth",
        output="screen",
        parameters=[
            {"topic": profile.truth_topic, "label": profile.truth_label, "use_sim_time": True}
        ],
        condition=IfCondition(LaunchConfiguration("publish_truth")),
    )
    spawn = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-topic",
            "robot_description",
            "-name",
            model_name,
            "-x",
            str(profile.spawn["x"]),
            "-y",
            str(profile.spawn["y"]),
            "-z",
            str(profile.spawn["z"]),
            "-Y",
            str(profile.spawn["yaw"]),
        ],
        output="screen",
    )

    staged: list[tuple[str, Node]] = [("spawn", spawn)]
    for name in profile.startup_order:
        staged.append(
            (
                name,
                Node(
                    package="controller_manager",
                    executable="spawner",
                    arguments=[
                        name,
                        "-c",
                        manager,
                        "--controller-manager-timeout",
                        "55",
                        "--switch-timeout",
                        "55",
                        "--service-call-timeout",
                        "55",
                    ],
                    output="screen",
                ),
            )
        )

    handlers = []
    for index, (stage, node) in enumerate(staged):
        next_stage = staged[index + 1] if index + 1 < len(staged) else None
        handlers.append(
            RegisterEventHandler(
                OnProcessExit(
                    target_action=node,
                    on_exit=_after_success(stage, next_stage, timeout_s),
                )
            )
        )

    support: list = [
        RegisterEventHandler(
            OnProcessExit(
                target_action=robot_state_publisher,
                on_exit=lambda event, context: _shutdown(
                    "robot_state_publisher", f"returncode={event.returncode}"
                ),
            )
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=clock_bridge,
                on_exit=lambda event, context: _shutdown(
                    "clock_bridge", f"returncode={event.returncode}"
                ),
            )
        ),
    ]
    bridge = None
    if profile.bridge_config is not None:
        bridge = Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            name="ros_gz_bridge",
            output="screen",
            parameters=[{"config_file": str(profile.bridge_config)}],
        )
        support.append(
            RegisterEventHandler(
                OnProcessExit(
                    target_action=bridge,
                    on_exit=lambda event, context: _shutdown(
                        "ros_gz_bridge", f"returncode={event.returncode}"
                    ),
                )
            )
        )

    timed = [spawn, clock_bridge]
    if bridge is not None:
        timed.append(bridge)

    return [
        *handlers,
        *support,
        _watchdog("spawn", timeout_s),
        gazebo,
        robot_state_publisher,
        truth,
        TimerAction(period=SPAWN_DELAY_SECONDS, actions=timed),
        LogInfo(
            msg=(
                f"robot profile selected: id={profile.robot_id} "
                f"joints={list(profile.joint_names)} "
                f"controller_profile={selection.profile} "
                f"controller_config={selection.realpath} sha256={selection.sha256}"
                + ("" if selection.gain is None else f" gain={selection.gain}")
                + f"; world={world} model={model_name} "
                f"controllers={list(profile.startup_order)} headless={headless}"
            )
        ),
    ]


def _launch_setup(context, *unused):
    profile = _load_robot(context)
    _require_model(profile)
    _apply_asset_prefix(profile)
    controller_profile = (
        LaunchConfiguration("controller_profile").perform(context).strip() or "default"
    )
    controller_config = LaunchConfiguration("controller_config").perform(context).strip()
    try:
        selection = profile.resolve_controller(controller_profile, controller_config)
    except (ControllerConfigError, OSError) as exc:
        raise RuntimeError(
            f"plant launch failure: stage=controller_config; robot={profile.robot_id}; {exc}"
        ) from exc
    description, notes = _robot_description(profile, selection.realpath)
    backend = LaunchConfiguration("backend").perform(context).strip().lower()
    if backend == "mock":
        actions = _mock_actions(context, profile, description)
    elif backend == "gz":
        actions = _gz_actions(context, profile, description, selection)
    else:
        raise RuntimeError(f"unknown backend {backend!r}; expected 'mock' or 'gz'")
    for note in notes:
        actions = [LogInfo(msg=f"URDF normalisation: {note}")] + actions
    return actions


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "robot",
                description="Robot id from the catalog (robots/<id>/robot.yaml)",
            ),
            DeclareLaunchArgument(
                "backend",
                default_value="mock",
                choices=["mock", "gz"],
                description="Plant backend: deterministic mock or Gazebo Harmonic",
            ),
            DeclareLaunchArgument(
                "domain_id",
                default_value="43",
                description="ROS domain; only 43 is accepted",
            ),
            DeclareLaunchArgument(
                "headless",
                default_value="true",
                description="Run Gazebo with the server only (gz backend)",
            ),
            DeclareLaunchArgument(
                "world",
                default_value="",
                description="World override; empty uses the profile world",
            ),
            DeclareLaunchArgument(
                "model_name",
                default_value="",
                description="Spawned model name override; empty uses the profile",
            ),
            DeclareLaunchArgument(
                "controller_profile",
                default_value="default",
                description="Controller profile from the robot profile (default or a named profile)",
            ),
            DeclareLaunchArgument(
                "controller_config",
                default_value="",
                description="Controller YAML override: absolute or robot-directory-relative",
            ),
            DeclareLaunchArgument(
                "controller_manager",
                default_value="",
                description="controller_manager node override; empty uses the profile",
            ),
            DeclareLaunchArgument(
                "startup_timeout",
                default_value="",
                description="Per-stage wall deadline; empty uses the profile",
            ),
            DeclareLaunchArgument(
                "publish_truth",
                default_value="true",
                description="Publish the profile's truth marker (gz backend)",
            ),
            SetEnvironmentVariable("ROS_DOMAIN_ID", LaunchConfiguration("domain_id")),
            SetEnvironmentVariable("GZ_PARTITION", "jcheng-sim"),
            OpaqueFunction(function=_validate_domain),
            OpaqueFunction(function=_launch_setup),
        ]
    )
