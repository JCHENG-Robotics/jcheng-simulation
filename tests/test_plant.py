"""Unit tests for the ROS-free joint plant."""

from pathlib import Path

import pytest

from jcheng_simulation_bringup.plant import JOINT_ORDER, JointPlant, load_joint_limits

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "ros2_ws" / "src" / "jcheng_simulation_bringup" / "config"
LIMITS = load_joint_limits(CONFIG / "joint_limits.yaml")


def test_limits_cover_every_command_joint():
    assert set(LIMITS) == set(JOINT_ORDER)
    for limit in LIMITS.values():
        assert limit.lower < limit.upper
        assert limit.velocity > 0.0


def test_targets_are_clamped_to_limits():
    plant = JointPlant(LIMITS)
    plant.set_targets({"joint1": 99.0, "r_joint": -99.0})
    assert plant.targets["joint1"] == LIMITS["joint1"].upper
    assert plant.targets["r_joint"] == LIMITS["r_joint"].lower


def test_unknown_joint_is_rejected():
    plant = JointPlant(LIMITS)
    with pytest.raises(ValueError):
        plant.set_targets({"finger_joint": 0.0})


def test_velocity_is_bounded_by_the_limit():
    plant = JointPlant(LIMITS, time_constant_s=0.01)
    plant.set_targets({"joint1": LIMITS["joint1"].upper})
    plant.step(0.01)
    assert abs(plant.velocities["joint1"]) <= LIMITS["joint1"].velocity + 1e-9


def test_plant_converges_and_snaps_to_target():
    plant = JointPlant(LIMITS, time_constant_s=0.05)
    plant.set_targets({"joint1": 0.5, "joint2": -0.2})
    for _ in range(400):
        plant.step(0.01)
    assert plant.positions["joint1"] == pytest.approx(0.5, abs=1e-9)
    assert plant.positions["joint2"] == pytest.approx(-0.2, abs=1e-9)
    assert plant.velocities["joint1"] == 0.0


def test_plant_is_deterministic():
    first = JointPlant(LIMITS)
    second = JointPlant(LIMITS)
    for _ in range(50):
        first.set_targets({"joint3": -0.4})
        second.set_targets({"joint3": -0.4})
        first.step(0.02)
        second.step(0.02)
    assert first.positions == second.positions
    assert first.velocities == second.velocities


def test_initial_pose_is_clamped():
    plant = JointPlant(LIMITS, initial={"joint1": 10.0, "r_joint": -0.4})
    assert plant.positions["joint1"] == LIMITS["joint1"].upper
    assert plant.positions["r_joint"] == -0.4


def test_invalid_step_is_rejected():
    plant = JointPlant(LIMITS)
    with pytest.raises(ValueError):
        plant.step(0.0)
    with pytest.raises(ValueError):
        plant.step(-0.1)
