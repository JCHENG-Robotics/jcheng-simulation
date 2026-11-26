#!/usr/bin/env bash
# Repository gate for jcheng-simulation. Run locally or from CI; it starts no
# Gazebo, no robot and no network service.
#
#   bash scripts/check_repo_gate.sh
#
# It checks the required files, Python syntax, XML well-formedness, the robot
# catalog, the no-hardware and domain-43 boundaries, the unit tests and
# relative doc links.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SRC="ros2_ws/src"
ENGINE="$SRC/jcheng_simulation_robots"
CATALOG="$ENGINE/robots"

fail() { printf 'GATE FAIL: %s\n' "$*" >&2; exit 1; }
step() { printf '== %s\n' "$*"; }

step "required files"
while IFS= read -r path; do
    [[ -e "$path" ]] || fail "missing $path"
done <<EOF
README.md
README.zh-CN.md
ROADMAP.md
ACCEPTANCE.md
VERSION
CHANGELOG.md
LICENSE-REVIEW.md
THIRD_PARTY_NOTICES.md
capability.yaml
pytest.ini
.github/workflows/ci.yml
.github/CODEOWNERS
scripts/check_repo_gate.sh
docs/ARCHITECTURE.md
docs/SIMULATION_MODEL.md
docs/FAILURE_MODES.md
docs/MULTI_ROBOT.md
docs/MIGRATION-2026-11-26-baseline-arm.md
docs/adr/0001-simulation-domain-and-truth.md
docs/adr/0002-second-plant-migrated-arm.md
docs/adr/0003-multi-robot-engine.md
evidence/20261126_offline_validation/README.md
evidence/20261126_migrated_arm/README.md
$ENGINE/package.xml
$ENGINE/setup.py
$ENGINE/launch/robot.launch.py
$ENGINE/launch/display.launch.py
$ENGINE/jcheng_simulation_robots/profile.py
$ENGINE/jcheng_simulation_robots/controller_config.py
$ENGINE/jcheng_simulation_robots/plant.py
$ENGINE/jcheng_simulation_robots/scan.py
$ENGINE/jcheng_simulation_robots/mock_node.py
$ENGINE/jcheng_simulation_robots/truth.py
$ENGINE/test/test_engine.py
$CATALOG/armpi_ultra/robot.yaml
$CATALOG/armpi_ultra/urdf/jcheng_armpi_sim.urdf.xacro
$CATALOG/armpi_ultra/config/controllers.yaml
$CATALOG/armpi_ultra/config/ros_gz_bridge.yaml
$CATALOG/armpi_ultra/worlds/jcheng_lab.sdf
$CATALOG/gate2_arm/robot.yaml
$CATALOG/gate2_arm/urdf/simple_arm.xacro
$CATALOG/gate2_arm/config/arm_controllers.yaml
$CATALOG/gate2_arm/config/arm_controllers_gain_0p1.yaml
$CATALOG/gate2_arm/config/arm_controllers_gain_0p2.yaml
$CATALOG/gate2_arm/worlds/arm_lab.sdf
$CATALOG/piper_x/robot.yaml
$CATALOG/piper_x/urdf/piper_x_gz.urdf.xacro
$CATALOG/piper_x/config/controllers.yaml
$CATALOG/piper_x/worlds/piper_x_lab.sdf
$SRC/jcheng_simulation_bringup/launch/sim.launch.py
$SRC/jcheng_simulation_arm/launch/gazebo.launch.py
tests/test_contract.py
tests/test_docs.py
tests/test_domain_isolation.py
tests/test_launch_wiring.py
tests/test_limits_consistency.py
tests/test_no_hardware.py
tests/test_plant.py
tests/test_profiles.py
tests/test_scan.py
tests/test_urdf.py
EOF

step "no LICENSE while the review is open"
[[ ! -e LICENSE ]] || fail "LICENSE must not be added before the review closes"

step "shell syntax"
bash -n scripts/check_repo_gate.sh || fail "bash -n scripts/check_repo_gate.sh"

step "python syntax"
while IFS= read -r file; do
    python3 -m py_compile "$file" || fail "py_compile $file"
done < <(find "$SRC" tests -name '*.py' -type f | grep -v __pycache__ | sort)

step "xml well-formedness"
python3 - <<'PY'
import xml.etree.ElementTree as ET
from pathlib import Path

files = sorted(Path("ros2_ws/src/jcheng_simulation_robots/robots").glob("*/urdf/*"))
files += sorted(Path("ros2_ws/src/jcheng_simulation_robots/robots").glob("*/worlds/*"))
assert files, "no catalog URDF or world found"
for path in files:
    ET.parse(path)
    print(f"parsed {path}")
PY

step "robot catalog"
PYTHONPATH="$SRC/jcheng_simulation_robots" python3 - <<'PY'
from pathlib import Path

from jcheng_simulation_robots.profile import load_catalog

root = Path("ros2_ws/src/jcheng_simulation_robots/robots")
profiles = load_catalog(root)
assert profiles, "empty robot catalog"
for robot_id, profile in sorted(profiles.items()):
    state = (
        "available"
        if profile.model_available
        else f"unavailable ({'; '.join(profile.missing_assets)})"
    )
    for controller_profile in ["default", *profile.controller_profiles]:
        selection = profile.resolve_controller(controller_profile)
        print(
            f"{robot_id}: joints={list(profile.joint_names)} "
            f"controller_profile={controller_profile} sha256={selection.sha256[:12]} "
            f"model={state}"
        )
PY

step "no-hardware scan"
if grep -rInE \
    '/dev/|serial\.Serial|serial_port|socketcan|can0|pigpio|spidev|gpio|ros_robot_controller|set_motor_speeds|bus_servo|lslidar|rplidar|v4l2|VideoCapture|usb_cam' \
    "$SRC" --include='*.py' --include='*.yaml' --include='*.yml' \
    --include='*.xacro' --include='*.sdf' --include='*.xml' \
    >/tmp/jcheng-sim-hardware-scan.txt 2>&1; then
    cat /tmp/jcheng-sim-hardware-scan.txt
    fail "hardware or vendor token found in a package"
fi

step "domain-43 scan"
if grep -rInE \
    '(ROS_DOMAIN_ID|domain_id)[[:space:]]*[:=][[:space:]]*["'"'"']?(0|41|42)\b' \
    "$SRC" --include='*.py' --include='*.yaml' --include='*.yml' \
    --include='*.xacro' --include='*.sdf' \
    >/tmp/jcheng-sim-domain-scan.txt 2>&1; then
    cat /tmp/jcheng-sim-domain-scan.txt
    fail "a robot domain (0/41/42) is assigned in source or config"
fi
grep -q 'default_value="43"' "$ENGINE/launch/robot.launch.py" || fail "the engine launch must default to domain 43"
grep -q 'GZ_PARTITION' "$ENGINE/launch/robot.launch.py" || fail "the engine launch must partition Gazebo transport"
grep -q 'robot:= is required' "$ENGINE/launch/robot.launch.py" || fail "the engine launch must require a robot id"

step "no vendor assets or model weights"
if find . -path ./.git -prune -o -type f \
    \( -iname '*.stl' -o -iname '*.dae' -o -iname '*.obj' \
       -o -iname '*.pt' -o -iname '*.onnx' -o -iname '*.engine' \) \
    -print | grep -q .; then
    fail "vendor mesh or model weight found in the tree"
fi

step "tests"
python3 -m pytest -q tests "$ENGINE/test"

step "docs links"
python3 - <<'PY'
import re
import sys
from pathlib import Path

docs = [Path("README.md"), Path("README.zh-CN.md"), *sorted(Path("docs").rglob("*.md"))]
docs += sorted(Path("evidence").rglob("README.md"))
problems = []
for doc in docs:
    text = doc.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path = target.split("#", 1)[0]
        if not path:
            continue
        if not (doc.parent / path).resolve().exists():
            problems.append(f"{doc}: {target}")
if problems:
    print("broken relative links:", *problems, sep="\n  ")
    sys.exit(1)
print(f"all relative links resolve ({len(docs)} documents)")
PY

step "gate OK"
