"""Domain-isolation checks: every plant is confined to domain 43."""

from pathlib import Path
import re

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "ros2_ws" / "src"
ENGINE = SRC / "jcheng_simulation_robots" / "launch" / "robot.launch.py"
DISPLAY = SRC / "jcheng_simulation_robots" / "launch" / "display.launch.py"
BRINGUP = SRC / "jcheng_simulation_bringup" / "launch" / "sim.launch.py"
ARM_GAZEBO = SRC / "jcheng_simulation_arm" / "launch" / "gazebo.launch.py"
ARM_DISPLAY = SRC / "jcheng_simulation_arm" / "launch" / "display.launch.py"
ENGINE_LAUNCHES = (ENGINE, DISPLAY)
WRAPPERS = {
    BRINGUP: "armpi_ultra",
    ARM_GAZEBO: "gate2_arm",
    ARM_DISPLAY: "gate2_arm",
}


@pytest.mark.parametrize("launch", ENGINE_LAUNCHES, ids=lambda path: path.name)
def test_engine_launch_rejects_any_other_domain(launch):
    source = launch.read_text(encoding="utf-8")
    assert "ROS_DOMAIN_ID" in source
    assert '!= "43"' in source
    assert "RuntimeError" in source
    assert 'default_value="43"' in source


def test_engine_partitions_gazebo_transport():
    source = ENGINE.read_text(encoding="utf-8")
    assert "GZ_PARTITION" in source
    assert "jcheng-sim" in source


@pytest.mark.parametrize(
    "launch,robot_id",
    sorted(WRAPPERS.items()),
    ids=[path.name for path in sorted(WRAPPERS)],
)
def test_compatibility_wrappers_pin_their_robot(launch, robot_id):
    source = launch.read_text(encoding="utf-8")
    assert robot_id in source
    assert "jcheng_simulation_robots" in source
    assert "SetEnvironmentVariable" not in source
    assert "ROS_DOMAIN_ID" not in source


def test_no_source_assigns_a_robot_domain():
    pattern = re.compile(
        r"""(ROS_DOMAIN_ID|domain_id)\s*[:=]\s*["']?(0|41|42)\b""",
        re.MULTILINE,
    )
    problems = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix not in {".py", ".yaml", ".yml", ".xacro", ".sdf", ".sh"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in pattern.finditer(text):
            problems.append(f"{path.relative_to(ROOT)}: {match.group(0)}")
    assert not problems, "robot-domain assignment found:\n" + "\n".join(problems)


def test_bridge_overrides_keep_ros_topics_under_sim():
    bridges = sorted((SRC / "jcheng_simulation_robots" / "robots").glob("*/config/*bridge*.yaml"))
    assert bridges
    for path in bridges:
        for entry in yaml.safe_load(path.read_text(encoding="utf-8")):
            ros_topic = entry["ros_topic_name"]
            assert ros_topic == "/clock" or ros_topic.startswith("/sim/"), ros_topic
            assert not ros_topic.startswith("/ros_robot_controller"), ros_topic


def test_manifest_domain_is_only_43():
    manifest = yaml.safe_load((ROOT / "capability.yaml").read_text(encoding="utf-8"))
    assert manifest["runtime"]["ros_domains"] == [43]
