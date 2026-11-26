"""Source-level checks for the generic launch's fail-closed wiring.

Behavioural event-wiring tests live in the package test
(``ros2_ws/src/jcheng_simulation_robots/test/test_engine.py``), which needs a
sourced ROS 2 environment. These checks run everywhere.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "ros2_ws" / "src" / "jcheng_simulation_robots" / "launch" / "robot.launch.py"
DISPLAY = ROOT / "ros2_ws" / "src" / "jcheng_simulation_robots" / "launch" / "display.launch.py"


def test_engine_is_fail_closed():
    source = ENGINE.read_text(encoding="utf-8")
    assert "if event.returncode == 0:" in source
    assert "RegisterEventHandler" in source
    assert "OnProcessExit" in source
    assert "profile.startup_order" in source
    assert 'on_exit_shutdown": "true' in source
    assert "wall deadline exceeded" in source


def test_engine_requires_a_robot_id_and_lists_the_catalog():
    source = ENGINE.read_text(encoding="utf-8")
    assert "robot:= is required" in source
    assert "catalog(robots_root)" in source


def test_engine_uses_the_profile_for_the_plant():
    source = ENGINE.read_text(encoding="utf-8")
    for token in (
        "profile.world",
        "profile.manager_node",
        "profile.startup_order",
        "profile.truth_topic",
        "profile.truth_label",
    ):
        assert token in source, token
    mock = (
        ROOT
        / "ros2_ws"
        / "src"
        / "jcheng_simulation_robots"
        / "jcheng_simulation_robots"
        / "mock_node.py"
    ).read_text(encoding="utf-8")
    assert "profile.joint_states_topic" in mock
    assert "profile.joint_command_topic" in mock


def test_engine_starts_the_sensor_bridge_only_when_configured():
    source = ENGINE.read_text(encoding="utf-8")
    assert "if profile.bridge_config is not None:" in source


def test_display_launch_is_domain_guarded_and_gui_optional():
    source = DISPLAY.read_text(encoding="utf-8")
    assert 'default_value="43"' in source
    assert "gui" in source
    assert "IfCondition" in source
