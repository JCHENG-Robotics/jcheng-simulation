# Piper X — asset manifest and plant notes

> Status: **reference manifest**, 2026-11-26. Not a plant, not loaded by
> `sim.launch.py`, and not a motion source.
> Geometry/inertia source of truth:
> `agilexrobotics/agx_arm_urdf@680fa925cd00db7e2628563d2edc5540963045de` (MIT).
> English canonical.

## 1. Why this directory exists

The tracked bringups are **text-only and mesh-free**: the ArmPi Ultra plant and
the migrated 2-DoF arm plant use primitive geometry, and the gate rejects every
`*.stl`, `*.dae` and `*.obj` in the tree (see the "no vendor assets or model
weights" step in [`scripts/check_repo_gate.sh`](../../../scripts/check_repo_gate.sh)).
The ecosystem has no robot-description/asset layer, and the only mesh precedent
is the frozen `jcheng-manipulation` description package, which must not be
reused.

Piper X therefore enters the ecosystem as four text-only pieces:

1. a pinned source manifest ([`SOURCES.yaml`](SOURCES.yaml));
2. a checked-in joint table ([`joint_map.yaml`](joint_map.yaml));
3. a fetch script that materialises the MIT assets **outside git**
   ([`scripts/fetch_piper_x_assets.sh`](../../../scripts/fetch_piper_x_assets.sh));
4. a catalog profile
   ([`robots/piper_x/robot.yaml`](../../../ros2_ws/src/jcheng_simulation_robots/robots/piper_x/robot.yaml))
   plus an in-tree Gazebo wrapper that includes the external URDF and adds the
   `ros2_control` block.

The mesh binaries live in `~/.local/share/jcheng/assets/piper_x/` (override with
`JCHENG_ASSET_ROOT`), not in this repository.

## 2. Pinned sources

| Source | Commit | Licence | Role |
|---|---|---|---|
| `agilexrobotics/agx_arm_urdf` | `680fa925cd00db7e2628563d2edc5540963045de` | MIT | Piper X URDF/xacro, meshes, inertials, joint limits; AGX gripper |
| `agilexrobotics/agx_arm_ros` (`ros2`) | `747d0722074d4cebc095d8d44f3ef68d2023ba6f` | MIT | ROS 2 driver, MoveIt2/SRDF/ros2_control, CAN/TCP docs |
| `agilexrobotics/piper_sdk` | `b847e5393a7ce6ff8508d713eca7bdd3a42421b4` | MIT | Legacy CAN SDK and V2/V3 protocol reference |
| `agilexrobotics/pyAgxArm` | `d90e234ba8e408cfa964b38aa9120b3131fc9f85` | LGPL-3.0 | Current SDK used by the driver; `ArmModel.PIPER_X` |

Detailed paths, hashes and the explicit **not fetched** list are in
[`SOURCES.yaml`](SOURCES.yaml).

## 3. Materialise and verify

```bash
# default: ~/.local/share/jcheng/assets/piper_x
bash scripts/fetch_piper_x_assets.sh

# or choose a root
JCHENG_ASSET_ROOT=/path/to/assets bash scripts/fetch_piper_x_assets.sh

# verify every upstream file
cd ~/.local/share/jcheng/assets/piper_x
sha256sum -c SHA256SUMS
```

The 2026-11-26 materialisation produced **618 upstream files / 38,673,663
bytes**, all checksums passing, 6 revolute joints and 0 missing mesh paths.
That is a reproducibility result, **not** a dynamics or hardware validation.

The asset bundle also carries `PROVENANCE.json` and the upstream `LICENSE` files.
`pyAgxArm` is LGPL-3.0; it is a dependency/reference, not code to paste into a
product repository.

## 4. Joint map

[`joint_map.yaml`](joint_map.yaml) transcribes the MIT URDF at the pinned commit.
Summary:

| Joint | Range | Sim note |
|---|---|---|
| `joint1` | ±2.6179938 rad (±150°) | revolute, axis `0 0 1` |
| `joint2` | 0…3.1415926 rad | revolute |
| `joint3` | -2.9670597…0 rad | revolute |
| `joint4` | ±1.553343 rad (±89°) | revolute |
| `joint5` | ±1.553343 rad (±89°) | revolute |
| `joint6` | ±2.9670597 rad (±170°) | revolute; public spec says ±165°, see below |
| `gripper` | 0…0.1 m | prismatic master joint |
| `gripper_joint1` | 0…0.05 m | mimic +0.5 |
| `gripper_joint2` | -0.05…0 m | mimic -0.5 |

The URDF `effort="100"` and `velocity="5"` are declarations, not measured
limits. The public Piper X specification lists J6 as ±165° (2.880 rad) while the
MIT URDF says ±170° (2.967 rad); until firmware and a bus read confirm it, a
plant should use the conservative 2.880 rad soft limit.

## 5. Plant status and how to run it

A catalog profile exists and is validated by the gate:

- `robots/piper_x/robot.yaml` — six revolute joints plus the prismatic
  `gripper`, controller YAML, world and mock config.
- `robots/piper_x/urdf/piper_x_gz.urdf.xacro` — in-tree wrapper that includes
  the external MIT description and adds the `ros2_control` block.
- `robots/piper_x/config/controllers.yaml` — arm + gripper JTCs with the
  default `position_proportional_gain` 10.

The external description is not in git, so the profile is **catalogued but not
launchable** until the bundle is materialised. The gate reports it:
`model=unavailable (env JCHENG_ASSET_ROOT; ...)`.

### 5.1 Materialise the assets and the ament prefix

```bash
bash scripts/fetch_piper_x_assets.sh          # 618 files under the asset root
export JCHENG_ASSET_ROOT=$HOME/.local/share/jcheng/assets
```

The upstream xacro includes `$(find agx_arm_description)/agx_arm_urdf/...` and
its meshes use `package://agx_arm_description/...`. The fetch script also
creates `<asset_root>/piper_x/prefix`, a minimal ament prefix whose
`agx_arm_description/agx_arm_urdf` links to the fetched URDF repo. The engine
prepends the profile's `asset_prefix` to `AMENT_PREFIX_PATH` and
`GZ_SIM_RESOURCE_PATH`, so no manual sourcing is needed:

```bash
ros2 launch jcheng_simulation_robots robot.launch.py robot:=piper_x backend:=mock
ros2 launch jcheng_simulation_robots robot.launch.py robot:=piper_x backend:=gz headless:=true
```

### 5.2 URDF normalisation

The upstream URDF omits `<inertial>` on `world` and `gripper_link`, and it
declares no joint damping. The engine inserts a 1 g placeholder inertial for
geometry-less links (otherwise URDF→SDF drops the master gripper link and the
mimic joints fail) and, because the profile sets `model.joint_damping: 1.0`,
adds `<dynamics damping="1">` to joints that have none. The asset files are
never modified.

### 5.3 Limitations (2026-11-26)

- Gazebo's physics engine does not support URDF mimic constraints; only the
  master `gripper` joint is commanded, the two finger joints do not follow.
- The headless DART build logs that some collision meshes (`base_link`,
  `link1`) could not be created. Physics runs from the inertials; do not claim
  contact or grasp fidelity.
- Tracking under gravity is not characterised: with the default gain 10 and
  damping 1.0, JTC goals complete (`error_code: 0`) with a residual error of up
  to ~0.04 rad on the 2026-11-26 run. The plant is for wiring/interface
  validation, not accuracy.
- J6 uses the conservative 2.880 rad soft limit (§4).
- No CAN access, no bridge, no hardware motion. The contract proposal and the
  safety review remain open.

## 6. Verification status

| Item | State |
|---|---|
| Profile schema, controllers, limits against `joint_map.yaml` | Verified (L0/L1, repository tests) |
| External URDF expansion and `ros2_control` wrapper | Verified (L0, engine test with assets) |
| Mock backend (7 joints, truth) | Verified (L2, 2026-11-26) |
| Gazebo backend (controllers active, arm + gripper goals) | Partially verified (L2, tracking uncharacterised) |
| Mimic finger motion | Not verified (physics-engine limitation) |
| MVE-3 TCP offset | Not started |
| MVE-4 CAN bridge | Not started (needs explicit hardware authorization) |

## 7. Licence rules

- **Adopt:** `agx_arm_urdf` and `agx_arm_ros` (MIT), `piper_sdk` (MIT), and
  `pyAgxArm` as an LGPL dependency.
- **Reference only, do not copy:** `agx_arm_sim` (README says MIT, no LICENSE),
  `piper_isaac_sim` (no LICENSE), `AB-pixel-pixel/piper-X` and
  `Mamengyiyi/PiperX-ToolKit` (no LICENSE).
- Generate Gazebo/MuJoCo/USD assets from the MIT URDF instead of importing the
  unlicensed prebuilt assets.
- Do not add a `LICENSE` file to this repository while the ecosystem licence
  review is open; the upstream licences stay in the external bundle.

## 8. Related

External working notes (not linked, to keep this repository self-contained):
`jcheng-research/references/manipulation/piper-x-assets.md`,
`jcheng-research/reports/20261126-piper-x-simulation-data-map.md`, and the
`jcheng-interfaces` proposal `docs/proposals/piper-x-robot-profile.md`.

- Current simulation model: [`SIMULATION_MODEL.md`](../../SIMULATION_MODEL.md)
- Repository gate: [`check_repo_gate.sh`](../../../scripts/check_repo_gate.sh)
