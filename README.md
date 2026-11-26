# jcheng-simulation

**English** | [简体中文](README.zh-CN.md)

The offline simulation plant for the JCHENG ecosystem: a deterministic mock
joint/scan plant and a Gazebo Harmonic bringup for a primitive ArmPi Ultra
model, both confined to ROS domain 43. It stands in for the vendor hardware
world during development and CI. It never opens a device, never joins domains
0/41/42, and never sends a motion command to the real system layer.

> Status: **Experimental**, partially verified (offline simulation) as of
> 2026-11-26, v0.1.0. The mock and Gazebo backends pass offline runs on
> Jazzy/Harmonic, but nothing here is hardware validation: the geometry is
> primitive and provisional, and the mobile base, second gripper finger and
> external camera are not modeled.
> English canonical; see [README.zh-CN.md](README.zh-CN.md) for the Chinese
> translation.

## Scope and boundary

| Item | This repository |
|---|---|
| Layer | SIM (offline, outside the L0–L4 runtime dependency graph) |
| Domain | **43 only**. The launch rejects any other `ROS_DOMAIN_ID`. |
| Inputs | Mock: `/sim/joint_command` (`sensor_msgs/JointState` position setpoints). Gazebo: `/sim/arm_controller/follow_joint_trajectory`, `/sim/gripper_controller/follow_joint_trajectory`. |
| Outputs | `/sim/joint_states`, `/sim/scan`, `/sim/camera/image`, `/sim/camera/camera_info`, `/sim/truth/source`; Gazebo also publishes `/clock`. |
| Hardware access | `none` (`capability.yaml`) |
| Owned devices | None. No `/dev/*`, serial, CAN, GPIO or camera device. |
| Motion authority | None on real hardware. The plant only simulates; it is never a `motion_source` for `jcheng-system`. |
| Forbidden | Domains 0/41/42, vendor topics, device access, real motion, vendor meshes, model weights. |

Every plant **data** topic is either `/clock` or under `/sim/`; the standard ROS
topics `/tf`, `/tf_static`, `/rosout`, `/parameter_events` and
`/robot_description` also exist. `/sim/truth/source` carries the literal
`simulated`; anything read from this repository is **simulated truth**, not a
measurement. Mock and Gazebo results are never reported as hardware validation.

### Manifest note

`capability-manifest.v1` (interfaces v0.1.0) constrains `runtime.ros_domains`
to `[42]` and requires `safety.requires_lease: true`. This repository is an
**offline plant**, so it deliberately declares `ros_domains: [43]` and
`requires_lease: false`, with `safety.class: offline`. The deviation is
asserted by `tests/test_contract.py` and tracked as M3 in [ROADMAP.md](ROADMAP.md);
it is not a silent schema violation.

## Repository layout

```text
jcheng-simulation/
├── capability.yaml                 # offline manifest; domain 43
├── docs/                           # architecture, model, failure modes, ADR
├── evidence/20261126_offline_validation/
├── scripts/check_repo_gate.sh
├── tests/                          # contract, boundary, plant, scan, docs
└── ros2_ws/src/jcheng_simulation_bringup/
    ├── config/                     # sim, limits, controllers, ros_gz bridge
    ├── launch/sim.launch.py        # backend:=mock|gz, domain guard
    ├── urdf/jcheng_armpi_sim.urdf.xacro
    ├── worlds/jcheng_lab.sdf
    └── jcheng_simulation_bringup/  # ROS-free plant/scan core + mock node
```

## Requirements

- **Simulation host:** ROS 2 Jazzy and Gazebo Sim (Harmonic, `gz sim` 8.x) for
  the `gz` backend. The host is an operator laptop/workstation, not the robot.
- **Mock backend:** ROS 2 with `rclpy`, `sensor_msgs` and `std_msgs`; no Gazebo.
- **Gazebo backend packages:** `ros_gz_sim`, `ros_gz_bridge`,
  `gz_ros2_control`, `joint_state_broadcaster`,
  `joint_trajectory_controller`, `robot_state_publisher`, `xacro`.
- **Contract:** `jcheng-interfaces` `>=0.1,<0.2`, contract hash
  `sha256:0b8d72ce…f24b42`.
- No hardware is required or accessed. The robot's Humble stack is not used by
  this repository.

## Quick start

```bash
cd jcheng-simulation
colcon build --base-paths ros2_ws/src --packages-select jcheng_simulation_bringup
source install/setup.bash
```

### Mock backend (deterministic, no Gazebo)

```bash
ros2 launch jcheng_simulation_bringup sim.launch.py backend:=mock
```

In another shell on domain 43:

```bash
export ROS_DOMAIN_ID=43
ros2 topic list | grep /sim
ros2 topic echo /sim/truth/source --once          # data: simulated
ros2 topic pub --once /sim/joint_command sensor_msgs/msg/JointState \
  "{name: ['joint1','r_joint'], position: [0.5,-1.0]}"
ros2 topic echo /sim/joint_states --once
```

The mock plant clamps setpoints to the joint limits, moves at a bounded
velocity, and holds the last targets after a 500 ms command gap. It publishes
a 360-beam synthetic scan at 10 Hz.

### Gazebo backend (headless by default)

```bash
ros2 launch jcheng_simulation_bringup sim.launch.py backend:=gz headless:=true
```

After the controller spawners finish (about 8–12 s of wall time), the arm is
commandable through the simulated controller action:

```bash
export ROS_DOMAIN_ID=43
ros2 action send_goal /sim/arm_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  "{trajectory: {joint_names: [joint1,joint2,joint3,joint4,joint5],
     points: [{positions: [0.3,0.2,-0.2,0.1,0.0],
               time_from_start: {sec: 2, nanosec: 0}}]}}"
```

For a GUI run pass `headless:=false` (not used in CI). The launch refuses any
`domain_id` other than `43`; do not override the domain.

## Tests

```bash
python3 -m pytest -q tests
bash scripts/check_repo_gate.sh
```

The suite covers the manifest contract, domain isolation, no-hardware and
vendor-asset scans, joint/scan models, limits consistency between the YAML,
URDF and controllers, and the documentation set.

## Validation status

| Claim | Level | Result | Evidence |
|---|---|---|---|
| Contract, boundary, domain and unit tests | L0/L1 | pass | `tests/` |
| Repository gate | L0 | pass | `scripts/check_repo_gate.sh` |
| URDF expansion and `gz sdf -p` | L0 | pass | [evidence](evidence/20261126_offline_validation/README.md) |
| Mock backend end-to-end | L2 | pass | same evidence |
| Gazebo backend end-to-end (headless) | L2 | pass | same evidence |
| Simulated joint trajectory via JTC | L2 | pass | same evidence |
| Hardware validation | L5 | **not applicable** | No hardware path exists |

The Gazebo run was on the operator host with Jazzy/Harmonic, not on the robot.
No hardware motion was commanded. Full report: [ACCEPTANCE.md](ACCEPTANCE.md).

## Related repositories

- `JCHENG-Robotics/jcheng-interfaces` — contract schema, hashes and evidence
  record schema.
- `JCHENG-Robotics/jcheng-system` — safety, authority, motion and hardware
  bridge; it also owns the scenario runner `jcheng_testkit` on domain 43.
- `JCHENG-Robotics/jcheng-perception` — advisory perception; a consumer of
  simulated sensor streams in future integration work.
- `JCHENG-Robotics/jcheng-ops` — operations; not involved in simulation.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — why this is a separate SIM
  layer and how it stays out of the runtime graph.

## License

**Pending.** This repository deliberately ships no `LICENSE` while the
organization review is open, matching `jcheng-interfaces`, `jcheng-system`,
`jcheng-perception`, `jcheng-ops` and `.github`. See
[LICENSE-REVIEW.md](LICENSE-REVIEW.md).
