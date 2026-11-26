#!/usr/bin/env bash
# Repository gate for jcheng-simulation. Run locally or from CI; it starts no
# Gazebo, no robot and no network service.
#
#   bash scripts/check_repo_gate.sh
#
# It checks the required files, Python syntax, XML well-formedness, the
# no-hardware and domain-43 boundaries, the unit tests and relative doc links.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PKG="ros2_ws/src/jcheng_simulation_bringup"

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
capability.yaml
pytest.ini
.github/workflows/ci.yml
.github/CODEOWNERS
scripts/check_repo_gate.sh
docs/ARCHITECTURE.md
docs/SIMULATION_MODEL.md
docs/FAILURE_MODES.md
docs/adr/0001-simulation-domain-and-truth.md
evidence/20261126_offline_validation/README.md
$PKG/package.xml
$PKG/setup.py
$PKG/launch/sim.launch.py
$PKG/urdf/jcheng_armpi_sim.urdf.xacro
$PKG/worlds/jcheng_lab.sdf
$PKG/config/sim.yaml
$PKG/config/joint_limits.yaml
$PKG/config/controllers.yaml
$PKG/config/ros_gz_bridge.yaml
tests/test_contract.py
tests/test_plant.py
tests/test_scan.py
tests/test_no_hardware.py
tests/test_domain_isolation.py
tests/test_limits_consistency.py
tests/test_docs.py
EOF

step "no LICENSE while the review is open"
[[ ! -e LICENSE ]] || fail "LICENSE must not be added before the review closes"

step "shell syntax"
bash -n scripts/check_repo_gate.sh || fail "bash -n scripts/check_repo_gate.sh"

step "python syntax"
while IFS= read -r file; do
    python3 -m py_compile "$file" || fail "py_compile $file"
done < <(find "$PKG" tests -name '*.py' -type f | sort)

step "xml well-formedness"
python3 - <<'PY'
import xml.etree.ElementTree as ET
from pathlib import Path

files = [
    Path("ros2_ws/src/jcheng_simulation_bringup/urdf/jcheng_armpi_sim.urdf.xacro"),
    Path("ros2_ws/src/jcheng_simulation_bringup/worlds/jcheng_lab.sdf"),
]
for path in files:
    ET.parse(path)
    print(f"parsed {path}")
PY

step "no-hardware scan"
if grep -rInE \
    '/dev/|serial\.Serial|serial_port|socketcan|can0|pigpio|spidev|gpio|ros_robot_controller|set_motor_speeds|bus_servo|lslidar|rplidar|v4l2|VideoCapture|usb_cam' \
    "$PKG" --include='*.py' --include='*.yaml' --include='*.yml' \
    --include='*.xacro' --include='*.sdf' --include='*.xml' \
    >/tmp/jcheng-sim-hardware-scan.txt 2>&1; then
    cat /tmp/jcheng-sim-hardware-scan.txt
    fail "hardware or vendor token found in the package"
fi

step "domain-43 scan"
if grep -rInE \
    '(ROS_DOMAIN_ID|domain_id)[[:space:]]*[:=][[:space:]]*["'"'"']?(0|41|42)\b' \
    "$PKG" --include='*.py' --include='*.yaml' --include='*.yml' \
    --include='*.xacro' --include='*.sdf' \
    >/tmp/jcheng-sim-domain-scan.txt 2>&1; then
    cat /tmp/jcheng-sim-domain-scan.txt
    fail "a robot domain (0/41/42) is assigned in source or config"
fi
grep -q 'domain_id: 43' "$PKG/config/sim.yaml" || fail "sim.yaml must pin domain_id: 43"

step "no vendor assets or model weights"
if find . -path ./.git -prune -o -type f \
    \( -iname '*.stl' -o -iname '*.dae' -o -iname '*.obj' \
       -o -iname '*.pt' -o -iname '*.onnx' -o -iname '*.engine' \) \
    -print | grep -q .; then
    fail "vendor mesh or model weight found in the tree"
fi

step "tests"
python3 -m pytest -q tests

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
