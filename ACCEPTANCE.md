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

## 7. Related

- [README](README.md)
- [ROADMAP](ROADMAP.md)
- [Offline validation evidence](evidence/20261126_offline_validation/README.md)
- [Architecture](docs/ARCHITECTURE.md)
