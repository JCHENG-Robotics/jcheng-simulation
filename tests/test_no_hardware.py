"""Static boundary check: no plant may touch hardware.

The scan covers every package under ``ros2_ws/src`` (engine, catalog data and
the compatibility wrappers). Documentation, tests and evidence are excluded
because they quote the forbidden tokens.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ros2_ws" / "src"
ROBOTS = SOURCE / "jcheng_simulation_robots" / "robots"

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
    for path in sorted(SOURCE.rglob("*")):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            if "__pycache__" in path.parts:
                continue
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


def test_catalog_urdfs_use_primitive_geometry_only():
    urdfs = sorted(ROBOTS.glob("*/urdf/*.xacro")) + sorted(ROBOTS.glob("*/urdf/*.urdf"))
    assert urdfs
    for urdf_path in urdfs:
        text = urdf_path.read_text(encoding="utf-8")
        assert "<mesh" not in text, urdf_path
        assert "package://" not in text, urdf_path
        assert "file://" not in text, urdf_path
