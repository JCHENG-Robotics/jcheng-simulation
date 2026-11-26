# Migration record — Gate-2 arm plant from the frozen baseline

> Date: 2026-11-26. Operator: JerichoCheng.
> Source: `jcheng-manipulation`, working tree at commit `a08b8b6`
> (2026-11-25, "feat(humble): make the laptop image the dev environment").
> Target: this repository. English canonical.

## 1. Why

`jcheng-manipulation` is frozen at `v1.0.0` and keeps the Gate-2 Gazebo
bringup (`ros2_ws/src/arm_description`) as part of its capstone evidence. That
bringup is simulation infrastructure, not a manipulation capability: it is a
2-DoF primitive arm used to prove `ros2_control` wiring, controller
configuration selection and a fail-closed startup chain. This repository owns
offline plants, so the code is **copied here and adapted**, and the baseline
is left untouched (its CI, evidence links and tags stay valid).

Scope, as agreed for this migration: only simulation code that satisfies the
existing boundaries. Vendor meshes, MoveIt configuration, mock grasp chains and
baseline evidence are **not** migrated; the disposition is in §3.

## 2. Source hashes

Working-tree files at `a08b8b6`; the baseline has unrelated uncommitted
changes (Studio/docs/tools), none in `arm_description`.

| Source file | SHA-256 |
|---|---|
| `ros2_ws/src/arm_description/urdf/simple_arm.xacro` | `a4f89f14aee8248bfc216e6b9929f1ae819d4b236e290c270aeb8111501314e1` |
| `ros2_ws/src/arm_description/launch/gazebo.launch.py` | `61cb84159e68cf4fe880b3edf585aabdee201462d0e422e708adf3efa54dc3b4` |
| `ros2_ws/src/arm_description/launch/display.launch.py` | `c55fa2dffbbf2ca7b602d9c52fd65b65d6bab146c1de402fa879ccfb86b2d424` |
| `ros2_ws/src/arm_description/config/arm_controllers.yaml` | `c85bf8015cb4db9a4d57df4e297189a3300d7b2da68ebd4893d9defc79d72af0` |
| `ros2_ws/src/arm_description/arm_description/controller_config.py` | `0a09592e78cdc878fac84e4062635db82acabb41d221129694a38e908ec0dfcb` |
| `ros2_ws/src/arm_description/test/test_controller_config.py` | `4a6114c961282c3f7a58ae8eb7a13e060506b74ba51775081f96a12721dc7e00` |

## 3. Disposition of every simulation-related baseline path

| Baseline path | Disposition | Reason |
|---|---|---|
| `ros2_ws/src/arm_description/` (xacro, Gazebo launch, 3 controller profiles, config resolver, tests) | **migrated** and adapted → `ros2_ws/src/jcheng_simulation_arm/` | Simulation infrastructure; no mesh, no vendor token, self-contained |
| `armpi_ultra_ws_clean/src/simulations/armpi_ultra_description/` (vendor whitelist description, 21 STL, 25 MB) | not migrated | Vendor meshes/URDF; `tests/test_no_hardware.py`, the gate and `docs/SIMULATION_MODEL.md` forbid them; vendor license review is open |
| `ros2_ws/src/armpi_ultra_description/` (modified copy, 21 STL, 17 MB) | not migrated | Same boundary, and it is referenced by the baseline CI, `tools/verify_config_consistency.py`, the grasp planner, MoveIt config and Studio |
| `ros2_ws/src/armpi_ultra_moveit_config/` | not migrated | MoveIt planning is out of scope (`ROADMAP.md`); it stays with the baseline and `jcheng-system` (plan-only) |
| `ros2_ws/src/arm_moveit_demo/` (Panda demo, `COLCON_IGNORE`) | not migrated | Not a plant; unreferenced upstream demo |
| `tools/phase2/measurement_protocol.py --mode simulate` and `evidence/phase2/session3_*/*_simulate.json` | not migrated | Synthetic measurement analysis, not a plant; the records belong to the baseline evidence chain |
| `tools/phase2/run_mock_visual_grasp_e2e.sh` and `armpi_grasp_planner/launch/mock_visual_grasp.launch.py` (domain 77) | not migrated | Mock grasp-planner chain, not a plant; outside the SIM layer |
| `week8_test_bag/` (94 s, 10 messages: `/rosout`, `/parameter_events`, `/events/write_split`) | not migrated | Contains no plant data |
| `evidence/phase3/session4_20261117/paired_trials_simulation*` | not migrated | Synthetic paired-trial analysis tied to the baseline evidence chain |
| `armpi-debug-studio` `--mock` adapter | not migrated | Studio application mock, not a simulation plant |

## 4. Changes made to the migrated code

| Item | Source | This repository | Why |
|---|---|---|---|
| Package name | `arm_description` | `jcheng_simulation_arm` | `jcheng_<capability>` naming; avoids a second package called `arm_description` in the ecosystem |
| ROS namespace | none (`/controller_manager`, `/arm_controller`) | `/sim/*` via the `gz_ros2_control` `<ros>` block | The plant must not publish an un-namespaced `/joint_states` on domain 43 |
| Controller YAML keys | `controller_manager`, `arm_controller`, `/gz_ros_control` | `/sim/controller_manager`, `/sim/arm_controller`, `/sim/gz_ros_control` | ROS 2 matches parameter files by fully qualified node name |
| Config hashes | — | `b0c1ad43…` (default), `3016246e…` (gain 0.1), `8b0c4365…` (gain 0.2) | Re-hashed after qualification; asserted by the package test |
| Launch domain | inherited from the environment | `domain_id` argument, default `43`, rejected otherwise; `GZ_PARTITION=jcheng-sim` | Domain isolation is this repository's first boundary |
| Startup stages | `gate2_*` completion keys | `arm_startup_*` completion keys | Drops baseline-specific naming; same fail-closed logic |
| Spawn | immediate | 3 s `TimerAction` for spawn + `/clock` bridge | Matches the proven pattern in `sim.launch.py`; `create` needs `/robot_description` |
| World | Gazebo builtin `empty.sdf` | `worlds/arm_lab.sdf` | Self-contained world, no builtin or Fuel dependency |
| `display.launch.py` | Broken: referenced an undefined `xacro_file_path` and a non-existent `simple_arm.urdf` | Rewritten: xacro expansion, domain-43 guard, `gui:=true` for RViz + joint GUI | The source could not run; copying it verbatim would ship dead code |
| URDF comments | Chinese | English | Repository language; numbers, axes, inertias and limits unchanged |
| URDF materials | no Gazebo material blocks | `<gazebo reference>` diffuse/ambient blocks | Visible model in the Gazebo GUI |
| Build | `ament_lint_auto` + copyright/cpplint skips | only `ament_cmake_pytest` | Keeps the package test; the repo gate owns style and compile checks |
| Package license tag | `Apache-2.0` | `Proprietary (license review pending; no LICENSE file)` | Matches the other package; the MIT notice is retained in `THIRD_PARTY_NOTICES.md` |

Numeric model data is unchanged: base cylinder r 0.10 m / h 0.10 m / 5.0 kg,
link1 r 0.05 / h 0.60 / 2.0 kg, link2 r 0.04 / h 0.40 / 1.0 kg, both joints
revolute about z, limits ±3.14159 rad, velocity 3.0, effort 100/50.

## 5. Verification performed

All offline, on the operator host (ROS 2 Jazzy, Gazebo Harmonic 8.x), domain
43, no hardware. Details and log excerpts:
[evidence/20261126_migrated_arm/README.md](../evidence/20261126_migrated_arm/README.md).

| Check | Result |
|---|---|
| `colcon build --packages-select jcheng_simulation_arm` | pass |
| Package test with ROS sourced (9 tests) | pass |
| Package test without ROS (4 pass, 5 launch tests skipped) | pass |
| `xacro simple_arm.xacro` | 166 lines |
| `gz sdf -p` URDF → SDF | 181 lines |
| `gz sdf -p worlds/arm_lab.sdf` | 68 lines |
| `ros2 launch … gazebo.launch.py --show-args` | pass |
| `ros2 launch … display.launch.py --show-args` | pass |
| Headless Gazebo plant, controllers active | ready in 3 s |
| `FollowJointTrajectory` to `[0.3, -0.2]` in 3 s | `error_code: 0`, `SUCCEEDED` |
| `/sim/joint_states` after the goal | `[0.29999999999999755, -0.19999999999999865]` |
| Repository gate (`tests` + package test) | pass (53 passed, 5 skipped without ROS) |

## 6. Not claimed

- No hardware access or motion; this is L2 offline simulation at most.
- No grasp, contact or payload claim: the model has two revolute joints and no
  gripper.
- No geometric accuracy: cylinder primitives, placeholder inertias.
- No controller-level limit enforcement: `gz_ros2_control` logs that command
  limits from the URDF are ignored (see [FAILURE_MODES.md](FAILURE_MODES.md)).
- The `gain_0p1` / `gain_0p2` profiles are validated as configuration, not
  characterized dynamically; only `default` was run end-to-end.
- The arm plant does not publish `/sim/truth/source`; like the existing Gazebo
  backend, only the mock plant does. Every data topic it does publish is
  `/sim`-prefixed. **(Superseded by §8: the engine's Gazebo backends now
  publish the truth marker.)**

## 7. Related

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [SIMULATION_MODEL.md](SIMULATION_MODEL.md)
- [FAILURE_MODES.md](FAILURE_MODES.md)
- [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)
- [Evidence 2026-11-26](../evidence/20261126_migrated_arm/README.md)

## 8. Layout update later the same day (ADR 0003)

The two-package split described above was replaced by one multi-robot engine
and a catalog:

| Before (this migration) | Now |
|---|---|
| `ros2_ws/src/jcheng_simulation_arm/urdf/simple_arm.xacro` | `ros2_ws/src/jcheng_simulation_robots/robots/gate2_arm/urdf/simple_arm.xacro` |
| `.../config/arm_controllers*.yaml` | `.../robots/gate2_arm/config/arm_controllers*.yaml` |
| `.../worlds/arm_lab.sdf` | `.../robots/gate2_arm/worlds/arm_lab.sdf` |
| `.../jcheng_simulation_arm/controller_config.py` | `.../jcheng_simulation_robots/controller_config.py` (generalized) |
| `.../launch/gazebo.launch.py` (staged chain) | `.../launch/robot.launch.py` (generic fail-closed chain) |
| `.../test/test_controller_config.py` | `.../test/test_engine.py` |
| `jcheng_simulation_arm` package | thin compatibility wrapper |

The provenance, MIT notice and boundary decisions in §1–§7 are unchanged; only
the file locations and the launch entry point moved. See
[ADR 0003](adr/0003-multi-robot-engine.md).
