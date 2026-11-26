"""Keep the profile limits, the URDF and the controller YAML in sync."""

from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml

from jcheng_simulation_robots.profile import load_catalog

ROOT = Path(__file__).resolve().parents[1]
PROFILES = load_catalog(ROOT / "ros2_ws" / "src" / "jcheng_simulation_robots" / "robots")
ROBOT_IDS = sorted(PROFILES)


def _urdf_joints(profile):
    tree = ET.parse(profile.urdf)
    joints = {}
    for joint in tree.iter("joint"):
        if joint.get("type") not in {"revolute", "prismatic", "continuous"}:
            continue
        limit = joint.find("limit")
        assert limit is not None, joint.get("name")
        joints[joint.get("name")] = (
            float(limit.get("lower")),
            float(limit.get("upper")),
            float(limit.get("velocity")),
        )
    return joints


@pytest.mark.parametrize("robot_id", ROBOT_IDS)
def test_urdf_limits_match_the_profile(robot_id):
    profile = PROFILES[robot_id]
    if profile.requires_env:
        pytest.skip("external model; see the joint-map and engine checks")
    urdf = _urdf_joints(profile)
    assert set(urdf) == set(profile.joint_names)
    for spec in profile.joints:
        lower, upper, velocity = urdf[spec.name]
        # The profile may tighten a limit (a soft limit), never widen it.
        assert spec.lower >= lower - 1e-9, spec.name
        assert spec.upper <= upper + 1e-9, spec.name
        assert spec.velocity <= velocity + 1e-9, spec.name


def test_piper_x_profile_stays_inside_the_reference_joint_map():
    reference = yaml.safe_load(
        (ROOT / "docs" / "robots" / "piper_x" / "joint_map.yaml").read_text(encoding="utf-8")
    )
    joints = {joint["name"]: joint for joint in reference["joints"]}
    expected = {
        name: (
            joints[name]["lower_rad"],
            joints[name]["upper_rad"],
            joints[name]["velocity_rad_s"],
            joints[name]["type"],
        )
        for name in ("joint1", "joint2", "joint3", "joint4", "joint5", "joint6")
    }
    master = reference["end_effector"]["master"]
    expected["gripper"] = (
        master["lower_m"],
        master["upper_m"],
        master["velocity_m_s"],
        master["type"],
    )
    profile = PROFILES["piper_x"]
    assert set(expected) == set(profile.joint_names)
    for spec in profile.joints:
        lower, upper, velocity, joint_type = expected[spec.name]
        assert spec.type == joint_type, spec.name
        assert spec.lower >= lower - 1e-9, spec.name
        assert spec.upper <= upper + 1e-9, spec.name
        assert spec.velocity <= velocity + 1e-9, spec.name


@pytest.mark.parametrize("robot_id", ROBOT_IDS)
def test_every_controller_profile_covers_the_profile_joints(robot_id):
    profile = PROFILES[robot_id]
    for controller_profile in ["default", *profile.controller_profiles]:
        selection = profile.resolve_controller(controller_profile)
        data = yaml.safe_load(selection.realpath.read_text(encoding="utf-8"))
        covered = []
        for controller in profile.controllers:
            if controller.kind != "trajectory":
                continue
            node = f"/sim/{controller.name}"
            joints = data[node]["ros__parameters"]["joints"]
            assert joints == list(controller.joints)
            covered.extend(joints)
        assert sorted(covered) == sorted(profile.joint_names)


@pytest.mark.parametrize("robot_id", ROBOT_IDS)
def test_command_interface_bounds_match_the_profile(robot_id):
    profile = PROFILES[robot_id]
    tree = ET.parse(profile.urdf)
    bounds = {}
    for control in tree.iter("ros2_control"):
        for joint in control.findall("joint"):
            command = joint.find("command_interface")
            if command is None:
                continue
            params = {
                param.get("name"): float(param.text) for param in command.findall("param")
            }
            if "min" in params and "max" in params:
                bounds[joint.get("name")] = (params["min"], params["max"])
    specs = {joint.name: joint for joint in profile.joints}
    for name, (lower, upper) in bounds.items():
        assert name in specs
        assert lower == pytest.approx(specs[name].lower)
        assert upper == pytest.approx(specs[name].upper)


@pytest.mark.parametrize("robot_id", ROBOT_IDS)
def test_world_is_valid_xml(robot_id):
    ET.parse(PROFILES[robot_id].world)
