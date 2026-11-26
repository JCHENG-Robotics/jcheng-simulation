"""Geometry, namespace and world checks for every catalog URDF."""

from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from jcheng_simulation_robots.profile import load_catalog

ROOT = Path(__file__).resolve().parents[1]
PROFILES = load_catalog(ROOT / "ros2_ws" / "src" / "jcheng_simulation_robots" / "robots")
ROBOT_IDS = sorted(PROFILES)


@pytest.mark.parametrize("robot_id", ROBOT_IDS)
def test_urdf_uses_primitive_geometry_only(robot_id):
    text = PROFILES[robot_id].urdf.read_text(encoding="utf-8")
    assert "<mesh" not in text
    assert "package://" not in text
    assert "file://" not in text


@pytest.mark.parametrize("robot_id", ROBOT_IDS)
def test_ros2_control_is_isolated_in_sim(robot_id):
    profile = PROFILES[robot_id]
    text = profile.urdf.read_text(encoding="utf-8")
    assert "<namespace>/sim</namespace>" in text
    assert "<remapping>robot_description:=/robot_description</remapping>" in text
    assert profile.controller_arg is not None
    assert f'<xacro:arg name="{profile.controller_arg}"' in text
    assert (
        f"$(find jcheng_simulation_robots)/robots/{robot_id}/config/" in text
    )


@pytest.mark.parametrize("robot_id", ROBOT_IDS)
def test_world_is_self_contained(robot_id):
    profile = PROFILES[robot_id]
    text = profile.world.read_text(encoding="utf-8")
    assert "fuel.ignitionrobotics.org" not in text
    assert "fuel.gazebosim.org" not in text
    assert "https://" not in text
    world = ET.parse(profile.world).getroot().find("world")
    assert world is not None
    plugins = " ".join(
        f"{plugin.get('filename')} {plugin.get('name')}" for plugin in world.findall("plugin")
    )
    assert "Physics" in plugins
    assert "SceneBroadcaster" in plugins


def test_world_sensor_plugins_match_the_declared_sensors():
    armpi = PROFILES["armpi_ultra"]
    gate2 = PROFILES["gate2_arm"]
    assert any(sensor.kind == "lidar" for sensor in armpi.sensors)
    assert any(sensor.kind == "camera" for sensor in armpi.sensors)
    assert "Sensors" in armpi.world.read_text(encoding="utf-8")
    assert "Sensors" not in gate2.world.read_text(encoding="utf-8")
    assert gate2.sensors == ()
