# ADR 0001 — Simulation domain, truth labeling and repository boundary

> Status: **Accepted**, 2026-11-26. v0.1.0.
> English canonical.

## Context

The ecosystem assigns four DDS domains: vendor 0, privileged 41, capability 42
and simulation 43 (`jcheng-system/configs/domains.yaml`). The simulation domain
currently hosts `jcheng_testkit` and mock vendor nodes, but there was no
separate virtual plant.

The ArmPi Ultra is a real robot with a vendor ROS 2 Humble stack, a bus-servo
arm and a 2D LiDAR. Developing and testing capability code without the robot
requires simulated joint states and sensor streams. Two mistakes are easy to
make:

1. Publishing simulated data on a robot domain or under a vendor topic name,
   so a consumer cannot tell it apart from hardware.
2. Treating a Gazebo or mock result as hardware validation.

## Decision

1. Create `jcheng-simulation` as a **SIM layer** repository, outside the L0–L4
   runtime dependency graph. No runtime repository imports it.
2. Confine every run to **domain 43**; the launch rejects any other
   `ROS_DOMAIN_ID`.
3. Prefix every ROS topic with `/sim/` (except `/clock`) and publish
   `/sim/truth/source = simulated`.
4. Never publish vendor topics (`/ros_robot_controller/*`, `bus_servo`,
   motor commands) and never open a device.
5. Keep `jcheng_testkit` as the scenario runner and report writer; this
   repository owns the plant, model, sensors and bridges.
6. Use primitive geometry, not vendor meshes, and document provisional values.
7. Declare `safety.class: offline`, `requires_lease: false` and
   `ros_domains: [43]` in `capability.yaml`, even though
   `capability-manifest.v1` constrains the last two differently. Track the
   schema revision as M3.

## Consequences

Positive:

- A capability can run against `/sim/scan` and `/sim/joint_states` without a
  robot, camera, or vendor container.
- Simulated data is visually and programmatically distinct from hardware.
- The plant has its own version, gate, evidence and license record.
- The two backends cover both fast deterministic tests (mock) and physics-based
  integration (Gazebo).

Negative / accepted:

- Two command interfaces exist in v0.1 (mock `JointState` setpoints vs Gazebo
  JTC actions); a scenario adapter is M5 work.
- The Gazebo path is Jazzy/Harmonic on the host, while the robot is Humble;
  the model cannot validate robot-bound timing.
- The model is primitive and single-fingered; grasp and accuracy claims are
  impossible.
- The capability manifest deviates from the v0.1 schema until interfaces M3.
- Domain isolation is not an SROS2 security boundary.

## Alternatives

| Alternative | Why not now |
|---|---|
| Put the plant in `jcheng-system/jcheng_testkit` | Couples reusable sensor/model assets to the system test runner and the system release cycle |
| Run the plant on domain 42 as a normal capability | It would appear in the capability graph and could be mistaken for a motion source; the design assigns simulation to 43 |
| Publish vendor topic names on 43 for drop-in compatibility | Consumers would learn the wrong names and a misconfigured process could cross domains; the `/sim` prefix is the safety property |
| Copy the vendor URDF and meshes | Violates the no-vendor-code rule and creates a licensing/provenance problem |
| Use only Gazebo, no mock | CI and unit tests need a deterministic, fast, ROS-free path |

## Related

- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [SIMULATION_MODEL.md](../SIMULATION_MODEL.md)
- [FAILURE_MODES.md](../FAILURE_MODES.md)
- [Repository taxonomy](https://github.com/JCHENG-Robotics/.github/blob/main/docs/repo-taxonomy.md)
