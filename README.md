# jcheng-simulation

**English** | [简体中文](README.zh-CN.md)

The offline simulation plant for the JCHENG ecosystem. It is a **multi-robot
engine**: one implementation, a catalog of devices, and two backends. Each
device is described by `robots/<id>/robot.yaml`; `robot.launch.py robot:=<id>`
builds a deterministic mock plant or a Gazebo Harmonic plant from that profile.
Everything is confined to ROS domain 43. Nothing opens a device, joins domains
0/41/42, or sends a motion command to the real system layer.

> Status: **Experimental**, partially verified (offline simulation) as of
> 2026-11-26, v0.1.0. The mock and Gazebo backends pass offline runs on
> Jazzy/Harmonic, but nothing here is hardware validation: the geometry is
> primitive and provisional, and no model has a second gripper finger, a depth
> stream or a mobile base. Two robots are in the catalog; adding a device is one
> directory plus a profile — see [docs/MULTI_ROBOT.md](docs/MULTI_ROBOT.md).
> English canonical; the Chinese README is a translation.

## Scope and boundary

| Item | This repository |
|---|---|
| Layer | SIM (offline, outside the L0–L4 runtime dependency graph) |
| Domain | **43 only**. Every launch rejects any other `ROS_DOMAIN_ID`. |
| Inputs | Mock: the profile's `joint_command` (`sensor_msgs/JointState` position setpoints). Gazebo: `/sim/<controller>/follow_joint_trajectory`. |
| Outputs | `/sim/joint_states`, the profile's sensor topics (ArmPi: `/sim/scan`, `/sim/camera/image`, `/sim/camera/camera_info`), `/sim/truth/source`; Gazebo also publishes `/clock`. |
| Hardware access | `none` (`capability.yaml`) |
| Owned devices | None. No `/dev/*`, serial, CAN, GPIO or camera device. |
| Motion authority | None on real hardware. The plant only simulates; it is never a `motion_source` for `jcheng-system`. |
| Forbidden | Domains 0/41/42, vendor topics, device access, real motion, vendor meshes, model weights. |

Every plant **data** topic is either `/clock` or under `/sim/`; the standard ROS
topics `/tf`, `/tf_static`, `/rosout`, `/parameter_events` and
`/robot_description` also exist. `/sim/truth/source` carries the literal
`simulated`; anything read from this repository is **simulated truth**, not a
measurement. Mock and Gazebo results are never reported as hardware validation.

## Robots

| Id | Model | Backends | Command joints | Sensors | Purpose |
|---|---|---|---|---|---|
| `armpi_ultra` | Primitive 5-DoF ArmPi Ultra stand-in | mock, gz | `joint1…joint5`, `r_joint` | lidar, wrist camera | Ecosystem plant: scan, camera, limits, truth |
| `gate2_arm` | Migrated 2-DoF Gate-2 arm | mock, gz | `joint1`, `joint2` | none | `ros2_control` wiring, controller profiles, fail-closed startup |
| `piper_x` | Piper X 6-DoF + parallel gripper (external MIT URDF) | mock, gz | `joint1…joint6`, `gripper` | none | External-asset example; real vendor description kept outside git |

`piper_x` needs the materialised asset bundle (`JCHENG_ASSET_ROOT`) and its
ament prefix; without them it is catalogued and validated but refuses to
launch. See [docs/robots/piper_x/](docs/robots/piper_x/README.md).

Both `/sim` naming, the `jcheng-sim` Gazebo partition and domain 43 apply to
every robot. Run **one plant at a time**: each claims `/sim/controller_manager`
and its controller actions. The Gazebo backends publish `/sim/truth/source`;
so does the mock backend.

### Adding a device

1. Create `ros2_ws/src/jcheng_simulation_robots/robots/<id>/` with a
   `robot.yaml`, a text-only URDF and its controller YAML.
2. Point `model.urdf` at the URDF (relative, absolute, or `$JCHENG_ASSET_ROOT`
   for an asset bundle kept outside git).
3. Run `bash scripts/check_repo_gate.sh`; it validates every profile and the
   URDF/controller consistency.

No Python, launch file or test file is copied. The schema reference, examples
and asset rules are in [docs/MULTI_ROBOT.md](docs/MULTI_ROBOT.md).

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
├── docs/                           # architecture, multi-robot schema, model, ADRs
├── evidence/20261126_offline_validation/
├── evidence/20261126_migrated_arm/
├── evidence/20261126_multi_robot_engine/
├── scripts/check_repo_gate.sh
├── tests/                          # contract, catalog, boundary, plant, scan, docs
└── ros2_ws/src/
    ├── jcheng_simulation_robots/    # THE engine
    │   ├── jcheng_simulation_robots/  # profile, controller config, plant, scan
    │   ├── launch/robot.launch.py     # robot:=..., backend:=mock|gz
    │   ├── launch/display.launch.py   # RViz, gui:=true
    │   ├── robots/armpi_ultra/        # profile + URDF + controllers + world + bridge
    │   ├── robots/gate2_arm/          # profile + URDF + controller profiles + world
    │   ├── robots/piper_x/            # profile + wrapper + controllers + world (external model)
    │   └── test/test_engine.py
    ├── jcheng_simulation_bringup/   # compatibility wrapper: ArmPi
    └── jcheng_simulation_arm/       # compatibility wrapper: Gate-2 arm
```

## Requirements

- **Simulation host:** ROS 2 Jazzy and Gazebo Sim (Harmonic, `gz sim` 8.x) for
  the `gz` backend. The host is an operator laptop/workstation, not the robot.
- **Mock backend:** ROS 2 with `rclpy`, `sensor_msgs` and `std_msgs`; no Gazebo.
- **Gazebo backend packages:** `ros_gz_sim`, `ros_gz_bridge`,
  `gz_ros2_control`, `joint_state_broadcaster`,
  `joint_trajectory_controller`, `robot_state_publisher`, `xacro`.
- **Engine build/test:** `ament_cmake_python`; `joint_state_publisher_gui` and
  `rviz2` only for `display.launch.py gui:=true`.
- **Contract:** `jcheng-interfaces` `>=0.1,<0.2`, contract hash
  `sha256:0b8d72ce…f24b42`.
- No hardware is required or accessed. The robot's Humble stack is not used by
  this repository.

## Quick start

```bash
cd jcheng-simulation
colcon build --base-paths ros2_ws/src \
  --packages-select jcheng_simulation_robots \
                   jcheng_simulation_bringup \
                   jcheng_simulation_arm
source install/setup.bash
```

### Mock backend (deterministic, no Gazebo)

```bash
ros2 launch jcheng_simulation_robots robot.launch.py \
  robot:=armpi_ultra backend:=mock
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

The mock plant clamps setpoints to the profile limits, moves at a bounded
velocity, and holds the last targets after a 500 ms command gap. When the
profile declares a scan, it publishes a 360-beam synthetic scan at 10 Hz;
`gate2_arm` declares none.

### Gazebo backend (headless by default)

```bash
ros2 launch jcheng_simulation_robots robot.launch.py \
  robot:=armpi_ultra backend:=gz headless:=true
```

Startup is fail-closed: `spawn` → `joint_state_broadcaster` →
`arm_controller` → `gripper_controller` (the profile's `startup_order`). A
stage starts only if the previous process exited 0, each stage has a wall
deadline (default 60 s), and a support-process exit shuts the launch down. The
selected controller YAML, its resolved path and its SHA-256 are logged before
Gazebo starts.

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

### The 2-DoF arm

Stop the ArmPi plant first: both claim `/sim/controller_manager`.

```bash
ros2 launch jcheng_simulation_robots robot.launch.py \
  robot:=gate2_arm backend:=gz headless:=true
```

```bash
export ROS_DOMAIN_ID=43
ros2 action send_goal /sim/arm_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  "{trajectory: {joint_names: [joint1, joint2],
     points: [{positions: [0.3, -0.2],
               time_from_start: {sec: 3, nanosec: 0}}]}}"
```

`controller_profile:=gain_0p1|gain_0p2` selects the profile's alternative
controller YAML (the V2 files set `gz_ros2_control`
`position_proportional_gain`). `controller_config:=<path>` overrides the YAML
(absolute or robot-directory-relative); it is schema-checked before launch.

### Display

```bash
ros2 launch jcheng_simulation_robots display.launch.py robot:=gate2_arm gui:=true
```

The display stays on domain 43 so a simulated robot TF never appears in a robot
graph.

### Compatibility entry points

The old commands still work; they include the engine with a fixed robot id:

```bash
ros2 launch jcheng_simulation_bringup sim.launch.py backend:=mock
ros2 launch jcheng_simulation_arm gazebo.launch.py
```

Prefer the engine form for new work.

## Tests

```bash
python3 -m pytest -q tests
python3 -m pytest -q ros2_ws/src/jcheng_simulation_robots/test
bash scripts/check_repo_gate.sh
```

The repository suite covers the manifest contract, the robot catalog and profile
schema, domain isolation, no-hardware and vendor-asset scans, joint/scan
models, limits consistency across the profile, URDF and controller YAML, the
fail-closed launch wiring and the documentation set. The engine package test
covers the strict controller-config resolver; its launch-wiring cases run only
when ROS 2 is sourced and skip otherwise.

## Validation status

| Claim | Level | Result | Evidence |
|---|---|---|---|
| Contract, catalog, boundary and unit tests | L0/L1 | pass | `tests/` |
| Repository gate (both catalog profiles) | L0 | pass | `scripts/check_repo_gate.sh` |
| Catalog URDF/SDF (both robots) | L0 | pass | [evidence](evidence/20261126_multi_robot_engine/README.md) |
| `armpi_ultra` mock backend end-to-end | L2 | pass | same evidence |
| `armpi_ultra` Gazebo backend and JTC trajectory | L2 | pass | same evidence |
| `gate2_arm` Gazebo backend and JTC trajectory | L2 | pass | same evidence |
| `piper_x` mock backend (7 joints, truth) | L2 | pass | same evidence |
| `piper_x` Gazebo backend (external MIT model, arm + gripper goals) | L2 | partially verified (tracking uncharacterised) | same evidence |
| Earlier single-package runs | L2 | historical | [2026-11-26 offline validation](evidence/20261126_offline_validation/README.md), [migrated arm](evidence/20261126_migrated_arm/README.md) |
| Hardware validation | L5 | **not applicable** | No hardware path exists |

The Gazebo runs were on the operator host with Jazzy/Harmonic, not on the
robot. No hardware motion was commanded. Full report: [ACCEPTANCE.md](ACCEPTANCE.md).

## Related repositories

- `JCHENG-Robotics/jcheng-interfaces` — contract schema, hashes and evidence
  record schema.
- `JCHENG-Robotics/jcheng-system` — safety, authority, motion and hardware
  bridge; it also owns the scenario runner `jcheng_testkit` on domain 43.
- `JCHENG-Robotics/jcheng-perception` — advisory perception; a consumer of
  simulated sensor streams in future integration work.
- `JCHENG-Robotics/jcheng-ops` — operations; not involved in simulation.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — why this is a separate SIM
  layer and how the engine stays out of the runtime graph.

## License

**Pending.** This repository deliberately ships no `LICENSE` while the
organization review is open, matching `jcheng-interfaces`, `jcheng-system`,
`jcheng-perception`, `jcheng-ops` and `.github`. See
[LICENSE-REVIEW.md](LICENSE-REVIEW.md). The code migrated from the MIT-licensed
`jcheng-manipulation` baseline retains its MIT notice in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md); no vendor asset is present.
