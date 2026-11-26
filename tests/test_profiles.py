"""Robot catalog and profile-schema tests."""

import shutil
from pathlib import Path

import pytest
import yaml

from jcheng_simulation_robots.controller_config import ControllerConfigError
from jcheng_simulation_robots.profile import (
    ProfileError,
    catalog,
    load_catalog,
    load_profile,
)

ROOT = Path(__file__).resolve().parents[1]
ROBOTS = ROOT / "ros2_ws" / "src" / "jcheng_simulation_robots" / "robots"
PROFILES = load_catalog(ROBOTS)
ROBOT_IDS = sorted(PROFILES)


def _copy(robot_id: str, tmp_path: Path) -> Path:
    destination = tmp_path / robot_id
    shutil.copytree(ROBOTS / robot_id, destination)
    return destination


def _edit(profile_path: Path, mutate) -> Path:
    data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    mutate(data)
    profile_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return profile_path


def test_catalog_lists_the_known_robots():
    assert ROBOT_IDS == ["armpi_ultra", "gate2_arm", "piper_x"]
    assert catalog(ROBOTS) == ROBOT_IDS


@pytest.mark.parametrize("robot_id", ROBOT_IDS)
def test_profile_is_self_consistent(robot_id):
    profile = PROFILES[robot_id]
    assert profile.joint_names
    assert len(set(profile.joint_names)) == len(profile.joint_names)
    assert set(profile.startup_order) == {item.name for item in profile.controllers}
    covered = [name for item in profile.controllers for name in item.joints]
    assert set(covered) == set(profile.joint_names)
    assert profile.manager_node.startswith("/sim/")
    assert profile.world.is_file()
    if profile.model_available:
        assert profile.urdf is not None and profile.urdf.is_file()
        assert profile.missing_assets == ()
    else:
        assert profile.missing_assets
    for sensor in profile.sensors:
        assert sensor.ros_topic.startswith("/sim/")
    if profile.sensors:
        assert profile.bridge_config is not None and profile.bridge_config.is_file()


def test_external_profile_reports_missing_assets(monkeypatch):
    monkeypatch.delenv("JCHENG_ASSET_ROOT", raising=False)
    profile = load_profile(ROBOTS / "piper_x" / "robot.yaml")
    assert profile.model_available is False
    assert any("JCHENG_ASSET_ROOT" in item for item in profile.missing_assets)
    # Controllers are still validated without the model.
    assert profile.resolve_controller().realpath.is_file()


def test_external_profile_is_available_with_the_bundle():
    profile = PROFILES["piper_x"]
    if not profile.model_available:
        pytest.skip(f"Piper X assets not materialised: {profile.missing_assets}")
    assert profile.requires_env == ("JCHENG_ASSET_ROOT",)
    assert profile.asset_prefix is not None and profile.asset_prefix.is_dir()


@pytest.mark.parametrize("robot_id", ROBOT_IDS)
def test_every_declared_controller_profile_resolves(robot_id):
    profile = PROFILES[robot_id]
    for controller_profile in ["default", *profile.controller_profiles]:
        selection = profile.resolve_controller(controller_profile)
        assert selection.realpath.is_file()
        assert len(selection.sha256) == 64
    for controller_profile in profile.controller_profiles:
        assert profile.resolve_controller(controller_profile).gain is not None


def test_gate2_gain_profiles_keep_the_declared_gain():
    profile = PROFILES["gate2_arm"]
    assert profile.resolve_controller("gain_0p1").gain == 0.1
    assert profile.resolve_controller("gain_0p2").gain == 0.2
    assert profile.resolve_controller("default").gain is None


def test_piper_x_default_uses_the_declared_gain():
    profile = PROFILES["piper_x"]
    selection = profile.resolve_controller()
    assert selection.gain == 10.0
    assert profile.default_gain == 10.0


def test_unknown_controller_profile_is_rejected():
    with pytest.raises(ControllerConfigError):
        PROFILES["gate2_arm"].resolve_controller("gain_0p9")


def test_profile_id_must_match_the_directory(tmp_path):
    copied = _copy("gate2_arm", tmp_path)
    renamed = tmp_path / "other_arm"
    copied.rename(renamed)
    with pytest.raises(ProfileError, match="directory name"):
        load_profile(renamed / "robot.yaml")


def test_duplicate_joint_is_rejected(tmp_path):
    copied = _copy("gate2_arm", tmp_path)
    _edit(copied / "robot.yaml", lambda data: data["joints"].append(dict(data["joints"][0])))
    with pytest.raises(ProfileError, match="duplicate joint"):
        load_profile(copied / "robot.yaml")


def test_controllers_must_cover_every_joint(tmp_path):
    copied = _copy("gate2_arm", tmp_path)

    def mutate(data):
        data["joints"].append(
            {"name": "joint3", "type": "revolute", "lower": -1.0, "upper": 1.0, "velocity": 1.0}
        )

    _edit(copied / "robot.yaml", mutate)
    with pytest.raises(ProfileError, match="cover exactly"):
        load_profile(copied / "robot.yaml")


def test_lower_bound_must_be_below_upper(tmp_path):
    copied = _copy("gate2_arm", tmp_path)
    _edit(copied / "robot.yaml", lambda data: data["joints"][0].__setitem__("lower", 9.0))
    with pytest.raises(ProfileError, match="lower must be < upper"):
        load_profile(copied / "robot.yaml")


def test_sensors_require_a_bridge(tmp_path):
    copied = _copy("armpi_ultra", tmp_path)
    _edit(copied / "robot.yaml", lambda data: data.pop("bridge"))
    with pytest.raises(ProfileError, match="bridge.config"):
        load_profile(copied / "robot.yaml")


def test_mock_scan_must_match_a_lidar_sensor(tmp_path):
    copied = _copy("armpi_ultra", tmp_path)
    _edit(copied / "robot.yaml", lambda data: data["mock"]["scan"].__setitem__("frame", "other"))
    with pytest.raises(ProfileError, match="declared lidar"):
        load_profile(copied / "robot.yaml")


def test_missing_urdf_is_reported(tmp_path):
    copied = _copy("gate2_arm", tmp_path)
    (copied / "urdf" / "simple_arm.xacro").unlink()
    with pytest.raises(ProfileError, match="model.urdf"):
        load_profile(copied / "robot.yaml")


def test_unqualified_controller_keys_are_rejected(tmp_path):
    copied = _copy("gate2_arm", tmp_path)
    config = copied / "config" / "arm_controllers.yaml"
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    data["arm_controller"] = data.pop("/sim/arm_controller")
    config.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(ControllerConfigError):
        load_profile(copied / "robot.yaml").resolve_controller()


def test_gain_mismatch_is_rejected(tmp_path):
    copied = _copy("gate2_arm", tmp_path)
    _edit(
        copied / "robot.yaml",
        lambda data: data["controllers"]["profiles"]["gain_0p1"].__setitem__("gain", 0.3),
    )
    profile = load_profile(copied / "robot.yaml")
    with pytest.raises(ControllerConfigError, match="position_proportional_gain"):
        profile.resolve_controller("gain_0p1")


def test_unknown_robot_has_a_clear_error():
    with pytest.raises(ProfileError, match="not found"):
        load_profile(ROBOTS / "missing_robot" / "robot.yaml")
