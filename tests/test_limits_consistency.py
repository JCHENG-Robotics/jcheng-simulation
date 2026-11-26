"""Keep the joint limits in the YAML, URDF and controllers in sync."""

from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml

from jcheng_simulation_bringup.plant import JOINT_ORDER

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ros2_ws" / "src" / "jcheng_simulation_bringup"
LIMITS = yaml.safe_load((PACKAGE / "config" / "joint_limits.yaml").read_text(encoding="utf-8"))[
    "joints"
]


def _revolute_joints():
    tree = ET.parse(PACKAGE / "urdf" / "jcheng_armpi_sim.urdf.xacro")
    joints = {}
    for joint in tree.iter("joint"):
        if joint.get("type") != "revolute":
            continue
        limit = joint.find("limit")
        assert limit is not None, joint.get("name")
        joints[joint.get("name")] = {
            "lower": float(limit.get("lower")),
            "upper": float(limit.get("upper")),
            "velocity": float(limit.get("velocity")),
        }
    return joints


def test_urdf_limits_match_the_yaml():
    urdf = _revolute_joints()
    assert set(urdf) == set(JOINT_ORDER)
    for name, expected in LIMITS.items():
        assert urdf[name]["lower"] == pytest.approx(expected["lower"])
        assert urdf[name]["upper"] == pytest.approx(expected["upper"])
        assert urdf[name]["velocity"] == pytest.approx(expected["velocity"])


def test_controllers_cover_exactly_the_command_joints():
    controllers = yaml.safe_load(
        (PACKAGE / "config" / "controllers.yaml").read_text(encoding="utf-8")
    )
    arm = controllers["/sim/arm_controller"]["ros__parameters"]["joints"]
    gripper = controllers["/sim/gripper_controller"]["ros__parameters"]["joints"]
    assert arm == list(JOINT_ORDER[:5])
    assert gripper == ["r_joint"]
    assert set(arm + gripper) == set(JOINT_ORDER)


def test_world_is_valid_xml():
    ET.parse(PACKAGE / "worlds" / "jcheng_lab.sdf")
