# jcheng-simulation roadmap

> Status: **v0.1.0** as of 2026-11-26. The fixed-base arm plant runs end-to-end
> in mock and Gazebo on Jazzy/Harmonic, offline only. The mobile base, the
> second gripper finger, the external camera and the contract revision are not
> started.

## Current state

| Item | State | Evidence |
|---|---|---|
| Contract, boundary and domain-43 skeleton | Complete (2026-11-26) | `capability.yaml`; `tests/` |
| Deterministic mock joint/scan plant | Complete (2026-11-26) | `ros2_ws/src/jcheng_simulation_bringup/`; L2 run |
| Gazebo Harmonic lab, URDF and controllers | Complete, offline (2026-11-26) | `evidence/20261126_offline_validation/README.md` |
| Simulated arm trajectory through JTC | Partially verified (simulation, 2026-11-26) | same evidence |
| Second gripper finger (`l_joint` mimic) | Not started | Single right finger only |
| External/wrist camera calibration model | Not started | Nominal camera mount only |
| Mobile base (wheels, LiDAR mount, Nav2) | Not started | Fixed-base model only |
| Scenario integration with `jcheng_testkit` | Planned | No cross-repo scenario yet |
| `capability-manifest.v1` revision for offline/domain 43 | Planned | Documented deviation only |

## Milestones

| Milestone | Scope | State | Exit criterion | Evidence |
|---|---|---|---|---|
| M0 | Contract-compliant SIM skeleton | Complete (2026-11-26) | Contract, boundary and domain tests pass | `tests/` |
| M1 | Deterministic mock plant | Complete (2026-11-26) | Joint setpoints move within limits; synthetic scan publishes | L2 run in evidence |
| M2 | Gazebo Harmonic fixed-base arm | Complete, offline (2026-11-26) | World loads; controllers active; JTC goal reaches the target | `evidence/20261126_offline_validation/README.md` |
| M3 | Contract revision for offline plants | Planned | `jcheng-interfaces` schema accepts `class: offline` with domain 43; all pins updated | — |
| M4 | Model fidelity and full gripper | Planned | Both fingers, measured link geometry and camera extrinsics documented | — |
| M5 | Scenario integration | Planned | `jcheng_testkit` drives the plant on domain 43 and records an L3 report | — |
| M6 | Mobile base plant | Planned | Diff-drive base, LiDAR mount and Nav2 input validated offline | — |

## Next

1. **M3 — contract revision.** Propose a `capability-manifest` revision in
   `jcheng-interfaces` that permits `safety.class: offline`,
   `requires_lease: false` and a simulation-only domain 43. Until then this
   repository keeps the documented local exception; do not change the values
   without the contract tag and hash update.
2. **M4 — model fidelity.** Add the `l_joint` mimic, replace the provisional
   link lengths with a documented read-only comparison against the vendor
   description, and add an external camera model. Do not copy vendor meshes
   into this repository.

## Out of scope

- Real hardware access of any kind: serial, CAN, GPIO, video devices, bus
  servos, motor bridge, e-stop.
- Runtime motion authority, leases, deadman, safety state machine and the
  vendor DDS domain; those stay in `jcheng-system`.
- MoveIt planning, perception algorithms and Nav2 policy; this repository only
  supplies a plant and sensor models.
- Vendor meshes, vendor source, model weights and recorded hardware data.
- Any claim that mock or Gazebo results validate the robot.

## Dependencies

- `jcheng-interfaces` `>=0.1,<0.2`, contract hash
  `sha256:0b8d72ced7f54d444d6851d8b99a51a78e2bed3f687324f51a15f76557f24b42`.
- `jcheng-system` API `>=0.1,<0.2` for future scenario integration; no runtime
  dependency in v0.1.
- Gazebo Harmonic and ROS 2 Jazzy on the simulation host. Robot-bound work
  remains Humble and requires separate operator authorization.
