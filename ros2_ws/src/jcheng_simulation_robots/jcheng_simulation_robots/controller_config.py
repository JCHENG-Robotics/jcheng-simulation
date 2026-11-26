"""Strict controller-configuration loading and selection.

The validation rules come from the Gate-2 bringup moved out of the frozen
baseline (``jcheng-manipulation`` ``arm_description``, commit a08b8b6). They are
now profile-driven so every robot in the catalog uses the same checks:

* exactly one UTF-8 YAML document, no anchors, aliases or tags;
* fully qualified node keys under the robot's controller-manager namespace;
* the declared controllers, their types, joints and interfaces must match the
  profile exactly;
* unknown keys, unqualified keys and wrong types are rejected, not ignored;
* the selected file is hashed and the hash is logged at launch.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml
from yaml.nodes import MappingNode, SequenceNode
from yaml.tokens import AliasToken, AnchorToken, TagToken

_FORBIDDEN_PATH_CHARS = ("\x00", "\n", "\r", "$")
_TRAJECTORY_OPTIONAL_KEYS = {
    "open_loop_control",
    "allow_nonzero_velocity_at_trajectory_start",
    "allow_partial_joints_goal",
}


class ControllerConfigError(ValueError):
    """A user-visible controller configuration validation failure."""


@dataclass(frozen=True)
class ControllerSelection:
    profile: str
    original_input: str
    logical_path: Path
    realpath: Path
    sha256: str
    gain: float | None


def load_strict_yaml(path: str | Path) -> tuple[dict[str, Any], bytes]:
    """Load one strict YAML mapping, rejecting anchors, aliases and tags."""

    source = Path(path)
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise ControllerConfigError(f"cannot read {source}: {exc}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ControllerConfigError(f"{source} is not UTF-8") from exc
    return load_strict_yaml_text(text, source), raw


def load_strict_yaml_text(text: str, source: str | Path = "<string>") -> dict[str, Any]:
    """Parse strict YAML text; see :func:`load_strict_yaml`."""

    try:
        tokens = list(yaml.scan(text))
        documents = list(yaml.compose_all(text))
    except yaml.YAMLError as exc:
        raise ControllerConfigError(f"{source}: invalid YAML: {exc}") from exc
    if any(isinstance(token, (AnchorToken, AliasToken, TagToken)) for token in tokens):
        raise ControllerConfigError(
            f"{source}: YAML anchors, aliases and tags are not allowed"
        )
    if len(documents) != 1 or documents[0] is None:
        raise ControllerConfigError(f"{source}: exactly one non-empty YAML document is required")

    def visit(node: Any) -> None:
        if isinstance(node, MappingNode):
            keys: set[str] = set()
            for key, value in node.value:
                if not isinstance(key.value, str) or key.value in keys:
                    raise ControllerConfigError(
                        f"{source}: duplicate or non-string YAML key: {key.value!r}"
                    )
                keys.add(key.value)
                visit(value)
        elif isinstance(node, SequenceNode):
            for item in node.value:
                visit(item)

    visit(documents[0])
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ControllerConfigError(f"{source}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ControllerConfigError(f"{source}: root must be a mapping")
    return data


def _resolve_input(robot_dir: Path, value: str) -> Path:
    if value != value.strip() or any(char in value for char in _FORBIDDEN_PATH_CHARS):
        raise ControllerConfigError(
            "controller_config contains forbidden whitespace/control/$ characters"
        )
    supplied = Path(os.path.expandvars(os.path.expanduser(value)))
    return supplied if supplied.is_absolute() else robot_dir / supplied


def _validate_manager(
    data: Mapping[str, Any],
    manager_node: str,
    declared: Iterable[tuple[str, str]],
    update_rate: int,
) -> None:
    try:
        params = data[manager_node]["ros__parameters"]
    except (KeyError, TypeError) as exc:
        raise ControllerConfigError(f"missing {manager_node}.ros__parameters mapping") from exc
    declared_names = {name for name, _ in declared}
    if not isinstance(params, dict) or set(params) != {"update_rate"} | declared_names:
        raise ControllerConfigError(
            f"{manager_node}.ros__parameters must contain update_rate and exactly "
            f"{sorted(declared_names)}"
        )
    if type(params["update_rate"]) is not int or params["update_rate"] != update_rate:
        raise ControllerConfigError(f"update_rate must be integer {update_rate}")
    for name, type_name in declared:
        if params[name] != {"type": type_name}:
            raise ControllerConfigError(f"invalid declaration for controller {name!r}")


def _validate_trajectory(
    data: Mapping[str, Any],
    node: str,
    joints: list[str],
    command_interfaces: list[str],
    state_interfaces: list[str],
) -> None:
    try:
        params = data[node]["ros__parameters"]
    except (KeyError, TypeError) as exc:
        raise ControllerConfigError(f"missing {node}.ros__parameters mapping") from exc
    required = {"joints", "command_interfaces", "state_interfaces"}
    if not isinstance(params, dict) or not required <= set(params):
        raise ControllerConfigError(f"{node}.ros__parameters is missing {sorted(required)}")
    unknown = set(params) - required - _TRAJECTORY_OPTIONAL_KEYS
    if unknown:
        raise ControllerConfigError(f"{node}.ros__parameters has unknown keys {sorted(unknown)}")
    if params["joints"] != joints:
        raise ControllerConfigError(f"{node}.joints must be {joints}")
    if params["command_interfaces"] != command_interfaces:
        raise ControllerConfigError(f"{node}.command_interfaces must be {command_interfaces}")
    if params["state_interfaces"] != state_interfaces:
        raise ControllerConfigError(f"{node}.state_interfaces must be {state_interfaces}")
    for key in _TRAJECTORY_OPTIONAL_KEYS & set(params):
        if type(params[key]) is not bool:
            raise ControllerConfigError(f"{node}.{key} must be a boolean")


def _controller_node(manager_node: str, name: str) -> str:
    if "/" in manager_node:
        prefix = manager_node.rsplit("/", 1)[0]
        return f"{prefix}/{name}" if prefix else f"/{name}"
    return name


def validate_controller_data(
    data: Mapping[str, Any],
    *,
    manager_node: str,
    update_rate: int,
    controllers: Iterable[Mapping[str, Any]],
    gain_node: str | None,
    expected_gain: float | None,
) -> None:
    """Validate one controller YAML against the profile declarations."""

    controllers = list(controllers)
    declared = [(item["name"], item["type"]) for item in controllers]
    expected_root = {manager_node} | {
        _controller_node(manager_node, item["name"])
        for item in controllers
        if item["kind"] == "trajectory"
    }
    include_gain = expected_gain is not None
    if include_gain:
        if gain_node is None:
            raise ControllerConfigError(
                "the profile declares a gain for this controller profile but no gain_node"
            )
        expected_root = expected_root | {gain_node}
    if set(data) != expected_root:
        raise ControllerConfigError(
            f"top-level keys must be exactly {sorted(expected_root)}, got {sorted(data)}"
        )
    _validate_manager(data, manager_node, declared, update_rate)
    for item in controllers:
        node = _controller_node(manager_node, item["name"])
        if item["kind"] == "trajectory":
            _validate_trajectory(
                data,
                node,
                item["joints"],
                item["command_interfaces"],
                item["state_interfaces"],
            )
        elif node in data:
            raise ControllerConfigError(
                f"{item['name']} is a broadcaster and must not have a parameter block"
            )
    if include_gain:
        try:
            gain_params = data[gain_node]["ros__parameters"]
            gain = gain_params["position_proportional_gain"]
        except (KeyError, TypeError) as exc:
            raise ControllerConfigError(
                f"{gain_node}.ros__parameters.position_proportional_gain is required"
            ) from exc
        if set(gain_params) != {"position_proportional_gain"}:
            raise ControllerConfigError(f"{gain_node}.ros__parameters has unknown keys")
        if type(gain) is not float or gain <= 0.0:
            raise ControllerConfigError("position_proportional_gain must be a positive float")
        if gain != expected_gain:
            raise ControllerConfigError(
                f"position_proportional_gain must be {expected_gain}, got {gain}"
            )


def resolve_controller_config(
    robot_dir: str | Path,
    *,
    controller_profile: str,
    controller_config: str,
    manager_node: str,
    update_rate: int,
    controllers: Iterable[Mapping[str, Any]],
    gain_node: str | None,
    default_file: str,
    profiles: Mapping[str, Mapping[str, Any]],
    default_gain: float | None = None,
) -> ControllerSelection:
    """Resolve, validate and hash the controller YAML for one profile."""

    robot_dir = Path(robot_dir)
    controllers = list(controllers)
    expected_gain: float | None = default_gain
    if controller_profile == "default":
        if controller_config:
            logical = _resolve_input(robot_dir, controller_config)
        else:
            logical = robot_dir / default_file
    else:
        if controller_profile not in profiles:
            raise ControllerConfigError(
                f"unsupported controller_profile {controller_profile!r}; "
                f"allowed: ['default', {', '.join(repr(name) for name in sorted(profiles))}]"
            )
        entry = profiles[controller_profile]
        expected_gain = float(entry["gain"]) if entry.get("gain") is not None else None
        if controller_config:
            logical = _resolve_input(robot_dir, controller_config)
        else:
            logical = robot_dir / entry["file"]
    try:
        resolved = logical.resolve(strict=True)
    except OSError as exc:
        raise ControllerConfigError(f"controller_config does not resolve: {logical}: {exc}") from exc
    if not resolved.is_file():
        raise ControllerConfigError(f"controller_config is not a regular file: {resolved}")
    data, raw = load_strict_yaml(resolved)
    validate_controller_data(
        data,
        manager_node=manager_node,
        update_rate=update_rate,
        controllers=controllers,
        gain_node=gain_node,
        expected_gain=expected_gain,
    )
    return ControllerSelection(
        profile=controller_profile,
        original_input=controller_config,
        logical_path=logical,
        realpath=resolved,
        sha256=hashlib.sha256(raw).hexdigest(),
        gain=expected_gain,
    )
