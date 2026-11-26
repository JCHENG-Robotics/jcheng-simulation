# Acceptance report — jcheng-simulation

> Status: **pass (offline simulation only)** as of 2026-11-26 for v0.1.0.
> Operator: JerichoCheng. Reviewer: pending.
> Scope: the capability contract, the domain-43 boundary, the no-hardware
> boundary, the deterministic mock plant, the Gazebo Harmonic plant and one
> simulated arm trajectory.
> **No hardware was accessed and no hardware motion was commanded.** L5 is not
> applicable because this repository has no hardware path.

## 1. Gates

| Gate | Command | Level | Result | Evidence |
|---|---|---|---|---|
| Contract, boundary and unit tests | `python3 -m pytest -q tests` | L0/L1 | pass (37 tests) | `tests/` |
| Repository gate | `bash scripts/check_repo_gate.sh` | L0 | pass | `scripts/check_repo_gate.sh` |
| URDF expansion | `xacro …` | L0 | pass (447 lines) | [evidence](evidence/20261126_offline_validation/README.md) |
| Robot and world SDF | `gz sdf -p …` | L0 | pass (589 / 159 lines) | same evidence |
| ROS build | `colcon build --packages-select jcheng_simulation_bringup` | L0 | pass | same evidence |
| Launch description | `ros2 launch … --show-args` | L0 | pass | same evidence |
| Mock backend end-to-end | `backend:=mock` on domain 43 | L2 | pass | same evidence |
| Gazebo backend end-to-end | `backend:=gz headless:=true` | L2 | pass | same evidence |
| Simulated arm trajectory | `FollowJointTrajectory` to `/sim/arm_controller` | L2 | pass | same evidence |
| Hardware | — | L5 | **not applicable** | No hardware path exists |

## 2. Verified claims

| Claim | Level | Evidence |
|---|---|---|
| The manifest declares `class: offline`, `hardware_access: none`, domain 43, no lease and a 500 ms mock command timeout | L0 | `capability.yaml`; `tests/test_contract.py` |
| The contract hash matches `jcheng-interfaces` v0.1.0 | L0 | `tests/test_contract.py` |
| The launch refuses any domain other than 43 | L0 | `tests/test_domain_isolation.py`; launch source |
| No device path, serial/CAN/GPIO token, vendor topic, vendor mesh or model weight exists in the package | L0 | `tests/test_no_hardware.py`; gate |
| The joint limits in YAML, URDF and controllers agree | L0 | `tests/test_limits_consistency.py` |
| The mock plant clamps targets, bounds velocity and settles deterministically | L1 | `tests/test_plant.py` |
| The synthetic scan hits the obstacle and walls at the expected ranges | L1 | `tests/test_scan.py` |
| The mock backend publishes joint states, scan and `truth=simulated` on domain 43 | L2 | [evidence](evidence/20261126_offline_validation/README.md) |
| The Gazebo backend activates the arm and gripper controllers and publishes joint states, scan and camera topics | L2 | same evidence |
| A simulated joint trajectory reaches the requested point (`error_code: 0`) | L2 | same evidence |

## 3. Not verified

| Item | Reason | Risk |
|---|---|---|
| Geometric accuracy and link lengths | Primitive, provisional geometry | Cannot be used for reach, collision or calibration claims |
| Grasp and contact behavior | Single finger; no grasp test | A simulated grasp would not represent the real gripper |
| Servo dynamics, backlash, current and temperature | Not modeled | Joint-space motion looks better than the real arm |
| LiDAR and camera accuracy | Sensor models are approximate; no calibration | Perception thresholds tuned here may not transfer |
| External/wrist camera extrinsic | Nominal mount only | Perception TF cannot be validated |
| Mobile base, Nav2 and `/cmd_vel` | Not modeled in v0.1 | No base integration evidence |
| Robot-bound Humble timing and Pi 5 load | Host is Jazzy/Harmonic | Real-time behavior remains unknown |
| Controller-level joint-limit enforcement | `gz_ros2_control` logs that command limits are disabled | Gazebo commands are not clamped by the controller |
| `capability-manifest.v1` compliance | Intentional domain/lease deviation | Automated admission using the v0.1 schema would reject the manifest |
| SROS2 or a security boundary on domain 43 | Not implemented | Domain isolation is environment-based |

## 4. Limitations

- This repository is a simulator. It has no e-stop, brake, bumper or
  safety-rated stop and cannot validate any of them.
- All ROS data is simulated truth: `/sim` names and
  `/sim/truth/source=simulated`. Never quote it as hardware measurement.
- Mock and Gazebo use different command interfaces; there is no unified
  scenario adapter yet.
- The Gazebo path targets ROS 2 Jazzy + Gazebo Harmonic on the operator host;
  the robot runs Humble. This is not a robot-bound validation.
- The model has one gripper finger; `l_joint` is a future milestone.
- The camera mount and world dimensions are provisional.
- The Gazebo run emitted a `libEGL` headless-rendering warning; sensor topics
  still published, but rendering fidelity is unverified.
- License status is pending; there is intentionally no `LICENSE` file.

## 5. Sign-off

| Role | Name | Date |
|---|---|---|
| Operator | JerichoCheng | 2026-11-26 |
| Reviewer | pending | — |

## 6. Machine-readable report

None. If one is produced later, it must validate against
`jcheng-interfaces/schemas/acceptance-report.v1.schema.json`.

## 7. Addendum — migrated 2-DoF arm plant (2026-11-26)

Second plant, added under [ADR 0002](docs/adr/0002-second-plant-migrated-arm.md).
Offline only; no hardware path. Full log excerpts:
[evidence/20261126_migrated_arm/README.md](evidence/20261126_migrated_arm/README.md).

| Gate | Command | Level | Result |
|---|---|---|---|
| Build | `colcon build --packages-select jcheng_simulation_arm` | L0 | pass |
| Package test (ROS sourced) | `python3 -m pytest -q ros2_ws/src/jcheng_simulation_arm/test` | L0/L1 | pass (9 tests) |
| URDF expansion | `xacro simple_arm.xacro` | L0 | pass (166 lines) |
| Robot and world SDF | `gz sdf -p …` | L0 | pass (181 / 68 lines) |
| Launch descriptions | `ros2 launch … --show-args` (both launches) | L0 | pass |
| Headless plant end-to-end | domain 43, controllers active after 3 s | L2 | pass |
| Simulated arm trajectory | `FollowJointTrajectory` to `[0.3, -0.2]` | L2 | pass (`error_code: 0`) |
| Repository gate | `bash scripts/check_repo_gate.sh` | L0 | pass (53 passed, 5 skipped without ROS) |

Not verified for this plant: geometric accuracy, grasp/contact, servo dynamics,
controller-level limit enforcement, runtime behavior of the `gain_0p1` /
`gain_0p2` profiles, GUI mode. At the time of this run `/sim/truth/source` was
not published by this plant (only the mock backend published it); the engine
addendum (§8) adds the truth publisher to every Gazebo backend. L5 remains
**not applicable**.

Sign-off: operator JerichoCheng, 2026-11-26; reviewer pending.

## 8. Addendum — multi-robot engine consolidation (2026-11-26)

The per-package plants were consolidated into one engine and a catalog under
[ADR 0003](docs/adr/0003-multi-robot-engine.md). Offline only; no hardware
path. Full log excerpts:
[evidence/20261126_multi_robot_engine/README.md](evidence/20261126_multi_robot_engine/README.md).

| Gate | Command | Level | Result |
|---|---|---|---|
| Build (engine + 2 wrappers) | `colcon build --packages-select jcheng_simulation_robots jcheng_simulation_bringup jcheng_simulation_arm` | L0 | pass |
| Repository + engine tests (ROS sourced) | `python3 -m pytest -q tests ros2_ws/src/jcheng_simulation_robots/test` | L0/L1 | pass (85 tests) |
| Catalog validation | `bash scripts/check_repo_gate.sh` | L0 | pass (2 profiles, 3 controller profiles) |
| `armpi_ultra` mock backend | engine, domain 43 | L2 | pass (joints, scan, truth) |
| `gate2_arm` mock backend | engine, domain 43 | L2 | pass (2 joints, no scan) |
| `gate2_arm` Gazebo backend | engine, headless | L2 | pass (3 s, JTC `error_code: 0`) |
| `armpi_ultra` Gazebo backend | engine, headless | L2 | pass (5 s, 3 controllers, scan + camera, JTC `error_code: 0`) |

The earlier single-package runs remain as historical evidence
([offline validation](evidence/20261126_offline_validation/README.md),
[migrated arm](evidence/20261126_migrated_arm/README.md)); their files moved
into the catalog and their startup path was replaced by the fail-closed chain.

Not verified in this addendum: geometric accuracy, grasp/contact, servo
dynamics, controller-level limit enforcement, runtime characterization of the
controller gain profiles, GUI mode. L5 remains **not applicable**.

Sign-off: operator JerichoCheng, 2026-11-26; reviewer pending.

## 9. Addendum — Piper X external-asset profile (2026-11-26)

Third catalog entry, pointing at the MIT description kept outside git. Offline
only; no hardware path. Details:
[evidence §11](evidence/20261126_multi_robot_engine/README.md) and
[docs/robots/piper_x/](docs/robots/piper_x/README.md).

| Gate | Command | Level | Result |
|---|---|---|---|
| Profile + controller validation without assets | `pytest -q tests` | L0/L1 | pass |
| Catalog reports `model=unavailable` without assets | `bash scripts/check_repo_gate.sh` | L0 | pass |
| External URDF expansion + wrapper (assets present) | engine test | L0 | pass |
| Mock backend (7 joints, truth, commands) | domain 43 | L2 | pass |
| Gazebo backend (controllers active, arm + gripper goals) | domain 43, headless | L2 | **partially verified** (residual ≤ ~0.04 rad; tracking uncharacterised) |

Not verified: mimic finger motion (physics-engine limitation), collision-mesh
fidelity, contact/grasp, tracking accuracy, CAN bridge and hardware. L5 remains
**not applicable**.

Sign-off: operator JerichoCheng, 2026-11-26; reviewer pending.

## 10. Related

- [README](README.md)
- [ROADMAP](ROADMAP.md)
- [Offline validation evidence](evidence/20261126_offline_validation/README.md)
- [Migrated arm evidence](evidence/20261126_migrated_arm/README.md)
- [Multi-robot engine evidence](evidence/20261126_multi_robot_engine/README.md)
- [Migration record](docs/MIGRATION-2026-11-26-baseline-arm.md)
- [Architecture](docs/ARCHITECTURE.md)
