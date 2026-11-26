"""Contract checks for the jcheng-simulation manifest and package."""

from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = yaml.safe_load((ROOT / "capability.yaml").read_text(encoding="utf-8"))

TOP_LEVEL = {
    "schema_version",
    "name",
    "version",
    "contract",
    "safety",
    "hardware_access",
    "runtime",
}
CONTRACT_HASH = (
    "sha256:0b8d72ced7f54d444d6851d8b99a51a78e2bed3f687324f51a15f76557f24b42"
)


def test_top_level_fields():
    assert set(MANIFEST) == TOP_LEVEL


def test_identity_and_version():
    assert MANIFEST["schema_version"] == 1
    assert MANIFEST["name"] == "jcheng-simulation"
    assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", MANIFEST["version"])
    assert MANIFEST["version"] == (ROOT / "VERSION").read_text().strip()


def test_contract_hash_and_ranges():
    contract = MANIFEST["contract"]
    assert set(contract) == {"interfaces", "contract_hash", "system_api"}
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", contract["contract_hash"])
    assert contract["contract_hash"] == CONTRACT_HASH
    assert contract["interfaces"] == ">=0.1,<0.2"
    assert contract["system_api"] == ">=0.1,<0.2"


def test_offline_class_never_consumes_a_lease():
    safety = MANIFEST["safety"]
    assert safety["class"] == "offline"
    assert safety["scopes"] == []
    # Deliberate deviation from capability-manifest.v1's const true: an offline
    # plant is not in the motion graph. See docs/ARCHITECTURE.md.
    assert safety["requires_lease"] is False
    assert safety["max_rate_hz"] == 50
    assert safety["deadman_ms"] == 500


def test_domain_43_is_declared_explicitly():
    # capability-manifest.v1 constrains ros_domains to [42]; the simulation
    # plant must run on 43. The deviation is intentional and documented.
    assert MANIFEST["runtime"]["ros_domains"] == [43]
    architecture = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "capability-manifest.v1" in architecture
    assert "43" in architecture


def test_hardware_access_is_none():
    assert MANIFEST["hardware_access"] == "none"


def test_runtime_surface_is_sim_namespaced():
    runtime = MANIFEST["runtime"]
    topics = runtime["publishes"] + runtime["subscribes"]
    assert topics
    for topic in topics:
        assert topic == "/clock" or topic.startswith("/sim/"), topic
    assert "/sim/joint_states" in runtime["publishes"]
    assert "/sim/truth/source" in runtime["publishes"]
    forbidden = (
        "ros_robot_controller",
        "set_motor_speeds",
        "/dev/",
        "bus_servo",
    )
    for topic in topics:
        assert not any(token in topic for token in forbidden), topic


def test_package_matches_manifest():
    package_xml = (
        ROOT
        / "ros2_ws"
        / "src"
        / "jcheng_simulation_bringup"
        / "package.xml"
    ).read_text(encoding="utf-8")
    assert "<name>jcheng_simulation_bringup</name>" in package_xml
    assert f"<version>{MANIFEST['version']}</version>" in package_xml
