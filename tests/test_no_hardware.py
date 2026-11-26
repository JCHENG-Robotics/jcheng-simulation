"""Static boundary check: the simulation must not touch hardware.

The scan covers source, launch, config, URDF and world files. Documentation,
tests and evidence are excluded because they quote the forbidden tokens.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ros2_ws" / "src" / "jcheng_simulation_bringup"
CONFIG = PACKAGE / "config"

TEXT_SUFFIXES = {".py", ".yaml", ".yml", ".xml", ".xacro", ".sdf", ".sh", ".cfg", ".txt"}

FORBIDDEN = (
    "/dev/",
    "serial.Serial",
    "serial_port",
    "socketcan",
    "can0",
    "pigpio",
    "spidev",
    "i2c",
    "gpio",
    "ros_robot_controller",
    "set_motor_speeds",
    "bus_servo",
    "lslidar",
    "rplidar",
    "v4l2",
    "VideoCapture",
    "usb_cam",
)

FORBIDDEN_ASSETS = {".stl", ".STL", ".dae", ".obj", ".pt", ".onnx", ".engine"}


def _scanned_files():
    # scripts/check_repo_gate.sh carries the forbidden-token list itself, so it
    # is excluded; the gate performs the same scan with its own patterns.
    for path in sorted(PACKAGE.rglob("*")):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            yield path


def test_no_hardware_tokens():
    problems = []
    for path in _scanned_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in FORBIDDEN:
            if token in text:
                problems.append(f"{path.relative_to(ROOT)}: {token}")
    assert not problems, "hardware tokens found:\n" + "\n".join(problems)


def test_no_vendor_assets_or_model_weights():
    found = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and path.suffix in FORBIDDEN_ASSETS
    ]
    assert not found, f"vendor assets or weights found: {found}"


def test_no_license_file_while_the_review_is_open():
    assert not (ROOT / "LICENSE").exists()
    assert (ROOT / "LICENSE-REVIEW.md").exists()


def test_package_uses_primitive_geometry_only():
    urdf = (PACKAGE / "urdf" / "jcheng_armpi_sim.urdf.xacro").read_text(
        encoding="utf-8"
    )
    assert "<mesh" not in urdf
    assert "package://" not in urdf
    assert "file://" not in urdf
