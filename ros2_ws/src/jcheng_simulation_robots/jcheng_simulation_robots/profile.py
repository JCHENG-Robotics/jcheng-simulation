"""Robot catalog: schema validation, resource resolution and profile lookup.

A *robot profile* is one YAML file per device under ``robots/<id>/robot.yaml``.
It is the single source of truth for the command joints, limits, controllers,
sensor topics, Gazebo world and mock behaviour. The generic launch builds a
plant from it; no per-device launch or Python code is needed.

The module is ROS-free so the catalog can be validated in the repository gate
without a ROS installation. Paths are resolved relative to the robot directory;
absolute paths and ``$JCHENG_ASSET_ROOT`` are allowed for assets kept outside
git (meshes, vendor URDFs).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .controller_config import (
    ControllerConfigError,
    ControllerSelection,
    load_strict_yaml,
    resolve_controller_config,
)

SCHEMA = "jcheng.simulation_robot.v1"
_JOINT_TYPES = {"revolute", "prismatic", "continuous"}
_SENSOR_KINDS = {"lidar", "camera", "depth"}


class ProfileError(ValueError):
    """A robot profile is missing, malformed or inconsistent."""


@dataclass(frozen=True)
class JointSpec:
    name: str
    type: str
    lower: float
    upper: float
    velocity: float
    effort: float | None


@dataclass(frozen=True)
class ControllerSpec:
    name: str
    kind: str
    type: str
    joints: tuple[str, ...] = ()
    command_interfaces: tuple[str, ...] = ()
    state_interfaces: tuple[str, ...] = ()


@dataclass(frozen=True)
class SensorSpec:
    name: str
    kind: str
    ros_topic: str
    frame: str
    rate_hz: float
    camera_info_topic: str | None = None


@dataclass(frozen=True)
class ScanSpec:
    topic: str
    frame: str
    rate_hz: float
    beam_count: int
    max_range_m: float
    angle_min_rad: float
    angle_max_rad: float
    range_min_m: float
    room: Mapping[str, float]


@dataclass(frozen=True)
class MockSpec:
    rate_hz: float
    time_constant_s: float
    command_timeout_ms: float
    initial: Mapping[str, float]
    scan: ScanSpec | None


@dataclass(frozen=True)
class Profile:
    robot_id: str
    version: str
    description: str
    root: Path
    model_name: str
    urdf: Path | None
    model_available: bool
    missing_assets: tuple[str, ...]
    requires_env: tuple[str, ...]
    asset_prefix: Path | None
    joint_damping: float | None
    default_gain: float | None
    controller_arg: str | None
    spawn: Mapping[str, float]
    joints: tuple[JointSpec, ...]
    controllers: tuple[ControllerSpec, ...]
    manager_node: str
    update_rate: int
    default_controller_config: str
    controller_profiles: Mapping[str, Mapping[str, Any]]
    gain_node: str | None
    startup_order: tuple[str, ...]
    startup_timeout_s: float
    sensors: tuple[SensorSpec, ...]
    bridge_config: Path | None
    world: Path
    mock: MockSpec
    joint_command_topic: str
    joint_states_topic: str
    truth_topic: str
    truth_label: str

    @property
    def joint_names(self) -> tuple[str, ...]:
        return tuple(joint.name for joint in self.joints)

    def controller(self, name: str) -> ControllerSpec:
        for item in self.controllers:
            if item.name == name:
                return item
        raise KeyError(name)

    def resolve_controller(
        self,
        controller_profile: str = "default",
        controller_config: str = "",
    ) -> ControllerSelection:
        return resolve_controller_config(
            self.root,
            controller_profile=controller_profile,
            controller_config=controller_config,
            manager_node=self.manager_node,
            update_rate=self.update_rate,
            controllers=[
                {
                    "name": item.name,
                    "kind": item.kind,
                    "type": item.type,
                    "joints": list(item.joints),
                    "command_interfaces": list(item.command_interfaces),
                    "state_interfaces": list(item.state_interfaces),
                }
                for item in self.controllers
            ],
            gain_node=self.gain_node,
            default_file=self.default_controller_config,
            profiles=self.controller_profiles,
            default_gain=self.default_gain,
        )


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ProfileError(f"{where} must be a mapping")
    return value


def _sequence(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProfileError(f"{where} must be a list")
    return value


def _string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProfileError(f"{where} must be a non-empty string")
    return value


def _number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProfileError(f"{where} must be a number")
    return float(value)


def _positive(value: Any, where: str) -> float:
    number = _number(value, where)
    if number <= 0.0:
        raise ProfileError(f"{where} must be > 0")
    return number


def _sim_topic(value: Any, where: str) -> str:
    topic = _string(value, where)
    if not topic.startswith("/sim/"):
        raise ProfileError(f"{where} must start with /sim/ (got {topic!r})")
    return topic


def _resolve(root: Path, value: str, where: str) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(value))
    path = Path(expanded)
    if not path.is_absolute():
        path = root / path
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ProfileError(
            f"{where} does not resolve: {path} (body: {exc}); external assets can be "
            "pointed at with $JCHENG_ASSET_ROOT"
        ) from exc
    if not resolved.is_file():
        raise ProfileError(f"{where} is not a regular file: {resolved}")
    return resolved


def _parse_joints(raw: Any) -> tuple[JointSpec, ...]:
    entries = _sequence(raw, "joints")
    if not entries:
        raise ProfileError("joints must not be empty")
    joints: list[JointSpec] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        where = f"joints[{index}]"
        item = _mapping(entry, where)
        name = _string(item.get("name"), f"{where}.name")
        if name in seen:
            raise ProfileError(f"duplicate joint {name!r}")
        seen.add(name)
        joint_type = _string(item.get("type", "revolute"), f"{where}.type")
        if joint_type not in _JOINT_TYPES:
            raise ProfileError(f"{where}.type must be one of {sorted(_JOINT_TYPES)}")
        lower = _number(item.get("lower"), f"{where}.lower")
        upper = _number(item.get("upper"), f"{where}.upper")
        if not lower < upper:
            raise ProfileError(f"{where}: lower must be < upper")
        velocity = _positive(item.get("velocity"), f"{where}.velocity")
        effort = item.get("effort")
        if effort is not None:
            effort = _number(effort, f"{where}.effort")
        joints.append(JointSpec(name, joint_type, lower, upper, velocity, effort))
    return tuple(joints)


def _parse_controllers(raw: Any) -> tuple[ControllerSpec, ...]:
    entries = _sequence(raw, "controllers.items")
    if not entries:
        raise ProfileError("controllers.items must not be empty")
    controllers: list[ControllerSpec] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        where = f"controllers.items[{index}]"
        item = _mapping(entry, where)
        name = _string(item.get("name"), f"{where}.name")
        if name in seen:
            raise ProfileError(f"duplicate controller {name!r}")
        seen.add(name)
        kind = _string(item.get("kind"), f"{where}.kind")
        if kind not in {"broadcaster", "trajectory"}:
            raise ProfileError(f"{where}.kind must be 'broadcaster' or 'trajectory'")
        controller_type = _string(item.get("type"), f"{where}.type")
        if kind == "broadcaster":
            controllers.append(ControllerSpec(name, kind, controller_type))
            continue
        joints = tuple(
            _string(value, f"{where}.joints[{i}]")
            for i, value in enumerate(_sequence(item.get("joints"), f"{where}.joints"))
        )
        if not joints:
            raise ProfileError(f"{where}.joints must not be empty")
        command = tuple(
            _string(value, f"{where}.command_interfaces[{i}]")
            for i, value in enumerate(
                _sequence(item.get("command_interfaces"), f"{where}.command_interfaces")
            )
        )
        state = tuple(
            _string(value, f"{where}.state_interfaces[{i}]")
            for i, value in enumerate(
                _sequence(item.get("state_interfaces"), f"{where}.state_interfaces")
            )
        )
        if not command or not state:
            raise ProfileError(f"{where}: command/state interfaces must not be empty")
        controllers.append(ControllerSpec(name, kind, controller_type, joints, command, state))
    return tuple(controllers)


def _parse_sensors(raw: Any) -> tuple[SensorSpec, ...]:
    entries = _sequence(raw, "sensors")
    sensors: list[SensorSpec] = []
    seen_topics: set[str] = set()
    for index, entry in enumerate(entries):
        where = f"sensors[{index}]"
        item = _mapping(entry, where)
        kind = _string(item.get("kind"), f"{where}.kind")
        if kind not in _SENSOR_KINDS:
            raise ProfileError(f"{where}.kind must be one of {sorted(_SENSOR_KINDS)}")
        topic = _sim_topic(item.get("ros_topic"), f"{where}.ros_topic")
        if topic in seen_topics:
            raise ProfileError(f"duplicate sensor topic {topic!r}")
        seen_topics.add(topic)
        camera_info = item.get("camera_info_topic")
        if camera_info is not None:
            camera_info = _sim_topic(camera_info, f"{where}.camera_info_topic")
        sensors.append(
            SensorSpec(
                name=_string(item.get("name"), f"{where}.name"),
                kind=kind,
                ros_topic=topic,
                frame=_string(item.get("frame"), f"{where}.frame"),
                rate_hz=_positive(item.get("rate_hz"), f"{where}.rate_hz"),
                camera_info_topic=camera_info,
            )
        )
    return tuple(sensors)


def _parse_scan(raw: Any, sensors: tuple[SensorSpec, ...]) -> ScanSpec | None:
    if raw is None:
        return None
    item = _mapping(raw, "mock.scan")
    topic = _sim_topic(item.get("topic"), "mock.scan.topic")
    frame = _string(item.get("frame"), "mock.scan.frame")
    lidars = [sensor for sensor in sensors if sensor.kind == "lidar"]
    if not any(sensor.ros_topic == topic and sensor.frame == frame for sensor in lidars):
        raise ProfileError(
            "mock.scan must match a declared lidar sensor (ros_topic and frame)"
        )
    room = _mapping(item.get("room"), "mock.scan.room")
    room_fields = {
        "width_m": _positive(room.get("width_m"), "mock.scan.room.width_m"),
        "depth_m": _positive(room.get("depth_m"), "mock.scan.room.depth_m"),
        "obstacle_x_m": _number(room.get("obstacle_x_m"), "mock.scan.room.obstacle_x_m"),
        "obstacle_y_m": _number(room.get("obstacle_y_m"), "mock.scan.room.obstacle_y_m"),
        "obstacle_radius_m": _positive(
            room.get("obstacle_radius_m"), "mock.scan.room.obstacle_radius_m"
        ),
    }
    beam_count = item.get("beam_count", 360)
    if isinstance(beam_count, bool) or not isinstance(beam_count, int) or beam_count < 2:
        raise ProfileError("mock.scan.beam_count must be an integer >= 2")
    angle_min = _number(item.get("angle_min_rad", -3.141592653589793), "mock.scan.angle_min_rad")
    angle_max = _number(item.get("angle_max_rad", 3.141592653589793), "mock.scan.angle_max_rad")
    if not angle_min < angle_max:
        raise ProfileError("mock.scan: angle_min_rad must be < angle_max_rad")
    return ScanSpec(
        topic=topic,
        frame=frame,
        rate_hz=_positive(item.get("rate_hz"), "mock.scan.rate_hz"),
        beam_count=beam_count,
        max_range_m=_positive(item.get("max_range_m"), "mock.scan.max_range_m"),
        angle_min_rad=angle_min,
        angle_max_rad=angle_max,
        range_min_m=_positive(item.get("range_min_m", 0.05), "mock.scan.range_min_m"),
        room=room_fields,
    )


def load_profile(path: str | Path) -> Profile:
    """Load and validate one ``robot.yaml``."""

    profile_path = Path(path)
    if not profile_path.is_file():
        raise ProfileError(f"robot profile not found: {profile_path}")
    data, _ = load_strict_yaml(profile_path)
    root = profile_path.parent
    schema = data.get("schema")
    if schema != SCHEMA:
        raise ProfileError(f"{profile_path}: schema must be {SCHEMA!r}, got {schema!r}")
    robot_id = _string(data.get("id"), "id")
    if robot_id != root.name:
        raise ProfileError(
            f"{profile_path}: id {robot_id!r} must equal the directory name {root.name!r}"
        )

    model = _mapping(data.get("model"), "model")
    controller_meta = _mapping(data.get("controllers"), "controllers")
    joints = _parse_joints(data.get("joints"))
    controllers = _parse_controllers(controller_meta.get("items"))
    sensors = _parse_sensors(data.get("sensors", []))

    command_joints: list[str] = []
    for controller in controllers:
        command_joints.extend(controller.joints)
    if len(command_joints) != len(set(command_joints)):
        raise ProfileError("a joint appears in more than one trajectory controller")
    if set(command_joints) != {joint.name for joint in joints}:
        raise ProfileError(
            "trajectory controllers must cover exactly the profile joints; "
            f"missing {sorted({j.name for j in joints} - set(command_joints))}, "
            f"extra {sorted(set(command_joints) - {j.name for j in joints})}"
        )

    manager_node = _string(controller_meta.get("manager", "/sim/controller_manager"), "controllers.manager")
    if not manager_node.startswith("/sim/"):
        raise ProfileError("controllers.manager must be under /sim/")
    update_rate = controller_meta.get("update_rate", 100)
    if isinstance(update_rate, bool) or not isinstance(update_rate, int) or update_rate <= 0:
        raise ProfileError("controllers.update_rate must be a positive integer")
    startup_order = tuple(
        _string(value, f"controllers.startup_order[{index}]")
        for index, value in enumerate(
            _sequence(controller_meta.get("startup_order"), "controllers.startup_order")
        )
    )
    declared = {controller.name for controller in controllers}
    if not startup_order or set(startup_order) != declared:
        raise ProfileError(
            f"controllers.startup_order must list exactly {sorted(declared)}"
        )
    profiles = _mapping(controller_meta.get("profiles", {}), "controllers.profiles")
    for name, entry in profiles.items():
        entry = _mapping(entry, f"controllers.profiles.{name}")
        _string(entry.get("file"), f"controllers.profiles.{name}.file")
        if entry.get("gain") is not None:
            _positive(entry["gain"], f"controllers.profiles.{name}.gain")
    gain_node = (
        _string(controller_meta["gain_node"], "controllers.gain_node")
        if controller_meta.get("gain_node") is not None
        else None
    )
    if any(entry.get("gain") is not None for entry in profiles.values()) and gain_node is None:
        raise ProfileError(
            "controllers.profiles with a gain require controllers.gain_node"
        )
    default_gain = None
    if controller_meta.get("default_gain") is not None:
        default_gain = _positive(
            controller_meta["default_gain"], "controllers.default_gain"
        )
        if gain_node is None:
            raise ProfileError(
                "controllers.default_gain requires controllers.gain_node"
            )

    bridge_raw = data.get("bridge")
    bridge_config = None
    if bridge_raw is not None:
        bridge = _mapping(bridge_raw, "bridge")
        bridge_config = _resolve(root, _string(bridge.get("config"), "bridge.config"), "bridge.config")
    if sensors and bridge_config is None:
        raise ProfileError("sensors require bridge.config (ros_gz_bridge mapping)")

    mock_raw = _mapping(data.get("mock"), "mock")
    scan = _parse_scan(mock_raw.get("scan"), sensors)
    initial = {
        _string(name, "mock.initial key"): _number(value, f"mock.initial.{name}")
        for name, value in _mapping(mock_raw.get("initial", {}), "mock.initial").items()
    }
    unknown_initial = set(initial) - {joint.name for joint in joints}
    if unknown_initial:
        raise ProfileError(f"mock.initial has unknown joints: {sorted(unknown_initial)}")

    topics = _mapping(data.get("topics"), "topics")
    truth = _mapping(data.get("truth"), "truth")
    spawn = _mapping(model.get("spawn", {}), "model.spawn")

    requires_env = tuple(
        _string(value, f"model.requires_env[{index}]")
        for index, value in enumerate(
            _sequence(model.get("requires_env", []), "model.requires_env")
        )
    )
    missing_assets: list[str] = [
        f"env {name}" for name in requires_env if not os.environ.get(name)
    ]
    asset_prefix = None
    if model.get("asset_prefix") is not None:
        raw_prefix = os.path.expandvars(
            os.path.expanduser(_string(model["asset_prefix"], "model.asset_prefix"))
        )
        if "$" in raw_prefix:
            missing_assets.append(f"asset prefix {raw_prefix}")
        else:
            candidate = Path(raw_prefix)
            if candidate.is_dir():
                asset_prefix = candidate.resolve()
            else:
                missing_assets.append(f"asset prefix {candidate}")
    urdf = None
    try:
        urdf = _resolve(root, _string(model.get("urdf"), "model.urdf"), "model.urdf")
    except ProfileError:
        # An external description may be absent on this host; the profile is
        # still catalogued and validated, but it cannot be launched.
        if not requires_env and asset_prefix is None:
            raise
        missing_assets.append("model.urdf")
    model_available = urdf is not None and not missing_assets
    joint_damping = None
    if model.get("joint_damping") is not None:
        joint_damping = _number(model["joint_damping"], "model.joint_damping")
        if joint_damping < 0.0:
            raise ProfileError("model.joint_damping must be >= 0")

    return Profile(
        robot_id=robot_id,
        version=_string(data.get("version", "0.0.0"), "version"),
        description=_string(data.get("description"), "description"),
        root=root.resolve(),
        model_name=_string(model.get("name"), "model.name"),
        urdf=urdf,
        model_available=model_available,
        missing_assets=tuple(missing_assets),
        requires_env=requires_env,
        asset_prefix=asset_prefix,
        joint_damping=joint_damping,
        default_gain=default_gain,
        controller_arg=(
            _string(model["controller_arg"], "model.controller_arg")
            if model.get("controller_arg") is not None
            else None
        ),
        spawn={
            "x": _number(spawn.get("x", 0.0), "model.spawn.x"),
            "y": _number(spawn.get("y", 0.0), "model.spawn.y"),
            "z": _number(spawn.get("z", 0.0), "model.spawn.z"),
            "yaw": _number(spawn.get("yaw", 0.0), "model.spawn.yaw"),
        },
        joints=joints,
        controllers=controllers,
        manager_node=manager_node,
        update_rate=update_rate,
        default_controller_config=_string(
            controller_meta.get("config"), "controllers.config"
        ),
        controller_profiles=profiles,
        gain_node=gain_node,
        startup_order=startup_order,
        startup_timeout_s=_positive(
            controller_meta.get("startup_timeout_s", 60.0), "controllers.startup_timeout_s"
        ),
        sensors=sensors,
        bridge_config=bridge_config,
        world=_resolve(root, _string(data.get("world"), "world"), "world"),
        mock=MockSpec(
            rate_hz=_positive(mock_raw.get("rate_hz"), "mock.rate_hz"),
            time_constant_s=_positive(mock_raw.get("time_constant_s"), "mock.time_constant_s"),
            command_timeout_ms=_positive(
                mock_raw.get("command_timeout_ms"), "mock.command_timeout_ms"
            ),
            initial=initial,
            scan=scan,
        ),
        joint_command_topic=_sim_topic(topics.get("joint_command"), "topics.joint_command"),
        joint_states_topic=_sim_topic(topics.get("joint_states"), "topics.joint_states"),
        truth_topic=_sim_topic(truth.get("topic"), "truth.topic"),
        truth_label=_string(truth.get("label"), "truth.label"),
    )


def catalog(robots_root: str | Path) -> list[str]:
    """Return the sorted robot ids under a ``robots/`` directory."""

    root = Path(robots_root)
    if not root.is_dir():
        raise ProfileError(f"robots directory not found: {root}")
    return sorted(
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and (entry / "robot.yaml").is_file()
    )


def load_catalog(robots_root: str | Path) -> dict[str, Profile]:
    """Load every profile under a ``robots/`` directory."""

    root = Path(robots_root)
    return {
        robot_id: load_profile(root / robot_id / "robot.yaml")
        for robot_id in catalog(root)
    }
