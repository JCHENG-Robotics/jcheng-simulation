# jcheng-simulation roadmap

> Status: **v0.1.0** as of 2026-11-26. A multi-robot catalog and a single plant
> engine run offline on Jazzy/Harmonic: `armpi_ultra` and `gate2_arm` on both
> backends, and `piper_x` from an external MIT description (mock verified,
> Gazebo partially verified). The mobile base, the second gripper finger, the
> external camera model and the contract revision are not started.

## Current state

| Item | State | Evidence |
|---|---|---|
| Contract, boundary and domain-43 skeleton | Complete (2026-11-26) | `capability.yaml`; `tests/` |
| Robot catalog and generic engine (`jcheng.simulation_robot.v1`) | Complete (2026-11-26) | `ros2_ws/src/jcheng_simulation_robots/`; `docs/MULTI_ROBOT.md` |
| `armpi_ultra` deterministic mock plant | Complete (2026-11-26) | engine run; `evidence/20261126_multi_robot_engine/` |
| `armpi_ultra` Gazebo plant, lidar, camera, gripper | Complete, offline (2026-11-26) | same evidence |
| `gate2_arm` Gazebo plant and controller profiles | Complete, offline (2026-11-26) | same evidence |
| `piper_x` profile from the external MIT description | Partially verified (2026-11-26) | `docs/robots/piper_x/`; evidence §12 |
| External-asset profiles (`requires_env`, `asset_prefix`) | Complete (2026-11-26) | engine tests; piper_x |
| Fail-closed startup chain (every Gazebo plant) | Complete, offline (2026-11-26) | same evidence |
| Compatibility entry points (`sim.launch.py`, `gazebo.launch.py`) | Deprecated but working (2026-11-26) | `ros2_ws/src/jcheng_simulation_{bringup,arm}/launch/` |
| Second gripper finger (`l_joint` mimic) | Not started | Single right finger in `armpi_ultra` |
| External/wrist camera calibration model | Not started | Nominal camera mount only |
| Mobile base (wheels, LiDAR mount, Nav2) | Not started | Fixed-base models only |
| Scenario integration with `jcheng_testkit` | Planned | No cross-repo scenario yet |
| `capability-manifest.v1` revision for offline/domain 43 | Planned | Documented deviation only |
| Third catalog device (Piper X) | Not started | Reference manifest only |

## Milestones

| Milestone | Scope | State | Exit criterion | Evidence |
|---|---|---|---|---|
| M0 | Contract-compliant SIM skeleton | Complete (2026-11-26) | Contract, boundary and domain tests pass | `tests/` |
| M1 | Deterministic mock plant | Complete (2026-11-26) | Joint setpoints move within limits; synthetic scan publishes | engine run in evidence |
| M2 | Gazebo Harmonic fixed-base arm | Complete, offline (2026-11-26) | World loads; controllers active; JTC goal reaches the target | `evidence/20261126_multi_robot_engine/` |
| M2b | Migrated 2-DoF arm plant | Complete, offline (2026-11-26) | Build, xacro/SDF, fail-closed startup and a JTC goal pass on domain 43 | same evidence |
| M2c | Multi-robot catalog + generic engine | Complete, offline (2026-11-26) | Two profiles, one launch, one gate, both backends | `docs/MULTI_ROBOT.md`; ADR 0003 |
| M3 | Contract revision for offline plants | Planned | `jcheng-interfaces` schema accepts `class: offline` with domain 43; all pins updated | — |
| M4 | Model fidelity and full gripper | Planned | Both fingers, measured link geometry and camera extrinsics documented | — |
| M5 | Scenario integration | Planned | `jcheng_testkit` drives a plant on domain 43 and records an L3 report | — |
| M6 | Mobile base plant | Planned | Diff-drive base, LiDAR mount and Nav2 input validated offline | — |
| M7 | External-asset device in the catalog | Complete, partially verified (2026-11-26) | A device whose URDF/meshes live under `$JCHENG_ASSET_ROOT` loads and runs | `docs/robots/piper_x/`; evidence §12 |

## Next

1. **M3 — contract revision.** Propose a `capability-manifest` revision in
   `jcheng-interfaces` that permits `safety.class: offline`,
   `requires_lease: false` and a simulation-only domain 43. Until then this
   repository keeps the documented local exception; do not change the values
   without the contract tag and hash update.
2. **M7 follow-up — Piper X fidelity.** Characterise and tune tracking under
   gravity (the default gain 10 + damping 1.0 leaves up to ~0.04 rad error and
   some oscillation), resolve the headless collision-mesh warnings, and decide
   how to represent the mimic fingers without physics-engine support.
3. **M4 — model fidelity.** Add the `l_joint` mimic to `armpi_ultra`, replace
   the provisional link lengths with a documented read-only comparison against
   the vendor description, and add an external camera model. Do not copy vendor
   meshes into this repository.
4. **Retire the compatibility wrappers.** Once recorded commands and evidence
   no longer reference `jcheng_simulation_bringup/sim.launch.py` and
   `jcheng_simulation_arm/gazebo.launch.py`, delete the two thin packages so the
   engine is the only entry point.

## Out of scope

- Real hardware access of any kind: serial, CAN, GPIO, video devices, bus
  servos, motor bridge, e-stop.
- Runtime motion authority, leases, deadman, safety state machine and the
  vendor DDS domain; those stay in `jcheng-system`.
- MoveIt planning, perception algorithms and Nav2 policy; this repository only
  supplies a plant and sensor models.
- Vendor meshes, vendor source, model weights and recorded hardware data.
- One package or launch per device; the catalog is the extension point.
- Any claim that mock or Gazebo results validate the robot.

## Dependencies

- `jcheng-interfaces` `>=0.2,<0.3`, contract hash
  `sha256:afca22a42f7163e0351d185d5a8577b0b51f2f3da4b92278f161a4a7d2c35b1c`.
- `jcheng-system` API `>=0.1,<0.2` for future scenario integration; no runtime
  dependency in v0.1.
- Gazebo Harmonic and ROS 2 Jazzy on the simulation host. Robot-bound work
  remains Humble and requires separate operator authorization.
