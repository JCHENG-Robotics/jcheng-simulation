"""Domain-isolation checks: simulation is confined to domain 43."""

from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ros2_ws" / "src" / "jcheng_simulation_bringup"
CONFIG = PACKAGE / "config"
LAUNCH = PACKAGE / "launch" / "sim.launch.py"


def test_config_declares_domain_43():
    config = yaml.safe_load((CONFIG / "sim.yaml").read_text(encoding="utf-8"))
    assert config["domain_id"] == 43
    assert config["truth"]["label"] == "simulated"
    assert config["truth"]["topic"] == "/sim/truth/source"


def test_launch_rejects_any_other_domain():
    source = LAUNCH.read_text(encoding="utf-8")
    assert "ROS_DOMAIN_ID" in source
    assert '!= "43"' in source
    assert "RuntimeError" in source
    assert 'default_value="43"' in source


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


def test_gazebo_transport_is_partitioned():
    source = LAUNCH.read_text(encoding="utf-8")
    assert 'GZ_PARTITION' in source
    assert 'jcheng-sim' in source


def test_bridge_keeps_ros_topics_under_sim():
    bridge = yaml.safe_load(
        (CONFIG / "ros_gz_bridge.yaml").read_text(encoding="utf-8")
    )
    for entry in bridge:
        ros_topic = entry["ros_topic_name"]
        assert ros_topic == "/clock" or ros_topic.startswith("/sim/"), ros_topic
        assert not ros_topic.startswith("/ros_robot_controller"), ros_topic


def test_manifest_domain_is_only_43():
    manifest = yaml.safe_load((ROOT / "capability.yaml").read_text(encoding="utf-8"))
    assert manifest["runtime"]["ros_domains"] == [43]
