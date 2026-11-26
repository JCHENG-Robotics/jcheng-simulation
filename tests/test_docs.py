"""Documentation set checks for the repository standard."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    "README.zh-CN.md",
    "ROADMAP.md",
    "CHANGELOG.md",
    "ACCEPTANCE.md",
    "LICENSE-REVIEW.md",
    "THIRD_PARTY_NOTICES.md",
    "VERSION",
    "capability.yaml",
    "docs/MULTI_ROBOT.md",
    "docs/MIGRATION-2026-11-26-baseline-arm.md",
    "docs/adr/0002-second-plant-migrated-arm.md",
    "docs/adr/0003-multi-robot-engine.md",
)


def test_required_documents_exist():
    for name in REQUIRED:
        assert (ROOT / name).is_file(), name


def test_readme_states_the_simulation_boundary():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "domain 43" in readme.lower() or "domain **43**" in readme
    assert "simulated" in readme.lower()
    assert "not hardware" in readme.lower() or "no hardware" in readme.lower()


def test_readme_documents_the_robot_catalog():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "robot:=armpi_ultra" in readme
    assert "robot:=gate2_arm" in readme
    assert "robots/<id>/robot.yaml" in readme


def test_acceptance_marks_hardware_as_not_applicable():
    acceptance = (ROOT / "ACCEPTANCE.md").read_text(encoding="utf-8")
    assert "L5" in acceptance
    assert "not applicable" in acceptance.lower()


def test_third_party_notices_keep_the_mit_notice_for_migrated_code():
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "MIT License" in notices
    assert "Copyright (c) 2026 Kewei (Jericho) Cheng" in notices
    assert "No vendor asset is present" in notices
    assert "robots/gate2_arm" in notices
