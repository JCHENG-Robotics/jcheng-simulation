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
    "VERSION",
    "capability.yaml",
)


def test_required_documents_exist():
    for name in REQUIRED:
        assert (ROOT / name).is_file(), name


def test_readme_states_the_simulation_boundary():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "domain 43" in readme.lower() or "domain **43**" in readme
    assert "simulated" in readme.lower()
    assert "not hardware" in readme.lower() or "no hardware" in readme.lower()


def test_acceptance_marks_hardware_as_not_applicable():
    acceptance = (ROOT / "ACCEPTANCE.md").read_text(encoding="utf-8")
    assert "L5" in acceptance
    assert "not applicable" in acceptance.lower()
