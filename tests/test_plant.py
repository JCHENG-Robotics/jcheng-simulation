"""Unit tests for the ROS-free joint plant (profile-driven)."""

from pathlib import Path

import pytest

from jcheng_simulation_robots.plant import JointLimit, JointPlant, validate_limits
from jcheng_simulation_robots.profile import load_catalog

ROOT = Path(__file__).resolve().parents[1]
PROFILES = load_catalog(ROOT / "ros2_ws" / "src" / "jcheng_simulation_robots" / "robots")


def _limits(profile):
    return {
        joint.name: JointLimit(joint.lower, joint.upper, joint.velocity)
        for joint in profile.joints
    }


ARM = PROFILES["armpi_ultra"]
LIMITS = _limits(ARM)
NAMES = ARM.joint_names


def test_limits_cover_every_command_joint():
    assert set(validate_limits(LIMITS, NAMES)) == set(NAMES)
    assert len(NAMES) == 6
    for limit in LIMITS.values():
        assert limit.lower < limit.upper
        assert limit.velocity > 0.0


def test_gate2_profile_drives_a_two_joint_plant():
    profile = PROFILES["gate2_arm"]
    plant = JointPlant(_limits(profile), profile.joint_names)
    assert plant.joint_names == ("joint1", "joint2")
    plant.set_targets({"joint1": 0.2})
    for _ in range(200):
        plant.step(0.01)
    assert plant.positions["joint1"] == pytest.approx(0.2, abs=1e-9)
    assert plant.positions["joint2"] == 0.0


def test_targets_are_clamped_to_limits():
    plant = JointPlant(LIMITS, NAMES)
    plant.set_targets({"joint1": 99.0, "r_joint": -99.0})
    assert plant.targets["joint1"] == LIMITS["joint1"].upper
    assert plant.targets["r_joint"] == LIMITS["r_joint"].lower


def test_unknown_joint_is_rejected():
    plant = JointPlant(LIMITS, NAMES)
    with pytest.raises(ValueError):
        plant.set_targets({"finger_joint": 0.0})


def test_velocity_is_bounded_by_the_limit():
    plant = JointPlant(LIMITS, NAMES, time_constant_s=0.01)
    plant.set_targets({"joint1": LIMITS["joint1"].upper})
    plant.step(0.01)
    assert abs(plant.velocities["joint1"]) <= LIMITS["joint1"].velocity + 1e-9


def test_plant_converges_and_snaps_to_target():
    plant = JointPlant(LIMITS, NAMES, time_constant_s=0.05)
    plant.set_targets({"joint1": 0.5, "joint2": -0.2})
    for _ in range(400):
        plant.step(0.01)
    assert plant.positions["joint1"] == pytest.approx(0.5, abs=1e-9)
    assert plant.positions["joint2"] == pytest.approx(-0.2, abs=1e-9)
    assert plant.velocities["joint1"] == 0.0


def test_validate_limits_rejects_gaps_duplicates_and_bad_bounds():
    with pytest.raises(ValueError):
        validate_limits(LIMITS, NAMES + ("missing",))
    with pytest.raises(ValueError):
        validate_limits(LIMITS, NAMES + (NAMES[0],))
    broken = dict(LIMITS)
    broken["joint1"] = JointLimit(1.0, -1.0, 1.5)
    with pytest.raises(ValueError):
        validate_limits(broken, NAMES)
