# Multi-robot plant catalog

> Status: **Experimental**, 2026-11-26. Three robots in the catalog
> (`armpi_ultra`, `gate2_arm`, `piper_x` — the last from an external MIT
> description); the engine and the catalog schema are
> `jcheng.simulation_robot.v1`. English canonical.

## 1. Why a catalog

The first version of this repository had one package per plant. That does not
scale: every new device repeated the launch, the limit checks, the controller
selection and the boundary tests. The engine inverts this:

- `ros2_ws/src/jcheng_simulation_robots/` is the **only** plant implementation.
- `robots/<id>/` holds one device's data: a `robot.yaml` profile, its URDF,
  controller YAML, optional Gazebo world and bridge mapping.
- `robot.launch.py robot:=<id>` builds either backend from the profile.
- Adding a device is **one directory plus a profile**. No Python or launch code
  is copied.

The compatibility packages `jcheng_simulation_bringup` and
`jcheng_simulation_arm` are kept only as thin entry points; they include the
engine with a fixed robot id.

## 2. Layout

```text
ros2_ws/src/jcheng_simulation_robots/
├── jcheng_simulation_robots/
│   ├── profile.py            # schema, catalog, path resolution (ROS-free)
│   ├── controller_config.py  # strict YAML selection and hashing (ROS-free)
│   ├── plant.py              # deterministic joint model (ROS-free)
│   ├── scan.py               # synthetic 2D scan (ROS-free)
│   ├── mock_node.py          # generic mock plant node
│   └── truth.py              # /sim/truth/source publisher for Gazebo
├── launch/
│   ├── robot.launch.py       # robot:=..., backend:=mock|gz
│   └── display.launch.py     # RViz display, gui:=true
├── robots/
│   ├── armpi_ultra/
│   │   ├── robot.yaml
│   │   ├── urdf/jcheng_armpi_sim.urdf.xacro
│   │   ├── config/controllers.yaml
│   │   ├── config/ros_gz_bridge.yaml
│   │   └── worlds/jcheng_lab.sdf
│   └── gate2_arm/
│       ├── robot.yaml
│       ├── urdf/simple_arm.xacro
│       ├── config/arm_controllers{,_gain_0p1,_gain_0p2}.yaml
│       └── worlds/arm_lab.sdf
├── robots/piper_x/
│   ├── robot.yaml                  # external MIT model; needs $JCHENG_ASSET_ROOT
│   ├── urdf/piper_x_gz.urdf.xacro  # wrapper: includes the external URDF, adds ros2_control
│   ├── config/controllers.yaml
│   └── worlds/piper_x_lab.sdf
└── test/test_engine.py
```

## 3. Profile schema (`jcheng.simulation_robot.v1`)

One YAML file per robot. The loader rejects unknown keys by construction (it
reads named fields only), duplicate joints, duplicate controllers, a joint that
no trajectory controller covers, a joint covered twice, bad bounds, non-`/sim`
topics and missing files.

### Top level

| Key | Required | Meaning |
|---|---|---|
| `schema` | yes | must be `jcheng.simulation_robot.v1` |
| `id` | yes | must equal the directory name |
| `version` | no | informational, default `0.0.0` |
| `description` | yes | one paragraph shown in docs/evidence |
| `model` | yes | URDF, controller arg, spawn pose |
| `joints` | yes | commandable joints and limits |
| `controllers` | yes | controller manager namespace, declarations, YAML files |
| `sensors` | no | ROS topics published through the Gazebo bridge (default `[]`) |
| `bridge` | with sensors | `ros_gz_bridge` config file |
| `world` | yes | Gazebo world file |
| `mock` | yes | mock plant rates, initial pose, optional scan |
| `topics` | yes | `/sim/joint_command` and `/sim/joint_states` |
| `truth` | yes | `/sim/truth/source` and its label |

### `model`

```yaml
model:
  name: jcheng_armpi_sim              # spawned Gazebo model name
  urdf: urdf/jcheng_armpi_sim.urdf.xacro
  controller_arg: controllers_yaml    # xacro arg that receives the controller YAML
  spawn: {x: 0.0, y: 0.0, z: 0.0, yaw: 0.0}

  # Optional, for a device whose description lives outside git:
  requires_env: [JCHENG_ASSET_ROOT]   # unset => catalogued but not launchable
  asset_prefix: ${JCHENG_ASSET_ROOT}/piper_x/prefix
  joint_damping: 1.0                  # add <dynamics damping> where absent
```

`urdf` is resolved relative to the robot directory. An absolute path or a value
using `$JCHENG_ASSET_ROOT` / `~` is allowed for assets kept outside git (see
§6); the file must exist when the profile is loaded, otherwise the launch fails
with the resolved path in the message.

`controller_arg` is the xacro argument the launch maps to the selected
controller YAML. Omit it if the URDF has no such argument.

`requires_env` lists environment variables that must be set for the model to be
launchable. If one is missing the profile still loads, the catalog and the
controller YAML are still validated, and the launch refuses with the missing
items. `asset_prefix` is a prefix directory (typically a small ament-style
`share/` tree) that the launch prepends to `AMENT_PREFIX_PATH` and to
`GZ_SIM_RESOURCE_PATH`, so the external URDF's `$(find ...)` includes and mesh
URIs resolve.

`joint_damping` (0 or positive) makes the launch add `<dynamics
damping="…">` to every revolute/prismatic joint that does not declare one. It
exists for vendor descriptions that omit damping and oscillate under a position
controller; it is off by default, so the primitive in-tree models are
unchanged.

### `joints`

```yaml
joints:
  - {name: joint1, type: revolute, lower: -1.8012, upper: 1.8012, velocity: 1.5, effort: 10.0}
```

`type` is `revolute`, `prismatic` or `continuous`. `lower < upper` and
`velocity > 0`; `effort` is optional. These are the **command** joints; mimic
joints stay in the URDF only. `tests/test_limits_consistency.py` asserts that
every profile joint appears in the URDF with the same bounds and that no extra
revolute/prismatic joint exists.

### `controllers`

```yaml
controllers:
  manager: /sim/controller_manager
  update_rate: 100
  config: config/controllers.yaml
  gain_node: /sim/gz_ros_control      # optional
  startup_order: [joint_state_broadcaster, arm_controller, gripper_controller]
  startup_timeout_s: 60.0
  profiles:                            # optional named YAML alternatives
    gain_0p1: {file: config/arm_controllers_gain_0p1.yaml, gain: 0.1}
  items:
    - {name: joint_state_broadcaster, kind: broadcaster, type: joint_state_broadcaster/JointStateBroadcaster}
    - name: arm_controller
      kind: trajectory
      type: joint_trajectory_controller/JointTrajectoryController
      joints: [joint1, joint2, joint3, joint4, joint5]
      command_interfaces: [position]
      state_interfaces: [position, velocity]
```

- `manager` must be under `/sim/`; controller nodes are derived from it
  (`/sim/<name>`).
- `startup_order` must list exactly the declared controllers; it is the spawn
  order of the fail-closed chain.
- A `broadcaster` has no parameter block; a `trajectory` controller declares its
  joints and interfaces, and the YAML must match exactly.
- `profiles` selects an alternative YAML with `controller_profile:=<name>`. A
  profile with `gain` requires `gain_node`; the YAML must contain
  `position_proportional_gain` equal to that value as a float.
- `default_gain` (optional) applies a `gain_node` value to the **default**
  profile too. `piper_x` uses `default_gain: 10.0`: with the plugin default
  (1.0) the shoulder and elbow cannot lift the real model under gravity.
- The selected YAML is loaded strictly: one document, no anchors/aliases/tags,
  no duplicate keys, exact top-level keys, exact schema. Its resolved path and
  SHA-256 are logged before Gazebo starts.

### `sensors` and `bridge`

```yaml
sensors:
  - {name: lidar, kind: lidar, ros_topic: /sim/scan, frame: laser_link, rate_hz: 10}
  - name: camera
    kind: camera
    ros_topic: /sim/camera/image
    camera_info_topic: /sim/camera/camera_info
    frame: camera_optical_frame
    rate_hz: 10

bridge:
  config: config/ros_gz_bridge.yaml
```

Sensor topics must start with `/sim/`; a non-empty `sensors` list requires
`bridge.config`. The bridge file is passed to `ros_gz_bridge` unchanged; every
ROS-side topic in it must be `/clock` or `/sim/*` (checked by the repository
tests). Camera/depth sensors are bridged for Gazebo only; the mock backend
publishes joints and, when declared, a lidar scan.

### `mock`

```yaml
mock:
  rate_hz: 50
  time_constant_s: 0.08
  command_timeout_ms: 500
  initial: {r_joint: -0.4}
  scan:
    topic: /sim/scan
    frame: laser_link
    rate_hz: 10
    beam_count: 360
    max_range_m: 8.0
    range_min_m: 0.05
    angle_min_rad: -3.141592653589793
    angle_max_rad: 3.141592653589793
    room: {width_m: 4.0, depth_m: 3.0, obstacle_x_m: 0.8, obstacle_y_m: 0.0, obstacle_radius_m: 0.15}
```

`scan` is optional and only valid when a `lidar` sensor with the same topic and
frame is declared. The mock holds the last targets after `command_timeout_ms`;
that is a simulator hold, not a safety stop.

### `topics` and `truth`

Both topics must be under `/sim/`. The truth label is published by the mock
node (mock backend) or by `truth_publisher` (Gazebo backend), transient-local.

## 4. Adding a device

1. `cp -r robots/gate2_arm robots/<id>` and rename the files you need.
2. Edit `robots/<id>/robot.yaml`: set `id: <id>` (must equal the directory),
   joints, controllers, sensors, world, mock.
3. Point `model.urdf` at the device's URDF. Either keep a text-only primitive
   URDF in the directory, or point at an external asset bundle (§6).
4. Run the gate. It loads every profile, resolves every controller profile and
   runs the consistency tests:

   ```bash
   bash scripts/check_repo_gate.sh
   ```

5. Smoke the mock backend:

   ```bash
   colcon build --base-paths ros2_ws/src --packages-select jcheng_simulation_robots
   source install/setup.bash
   ros2 launch jcheng_simulation_robots robot.launch.py robot:=<id> backend:=mock
   ```

No new package, launch file or test file is required. If the device needs a new
sensor kind or controller kind, that is an engine change — add it to the schema,
the launch and the tests together.

## 5. Backends

| | `backend:=mock` | `backend:=gz` |
|---|---|---|
| Runtime | ROS 2 only | ROS 2 Jazzy + Gazebo Harmonic |
| Command | profile `joint_command` (`JointState` positions) | `<manager>/<controller>/follow_joint_trajectory` |
| Joint state | profile `joint_states` at `mock.rate_hz` | `joint_state_broadcaster` |
| Scan | synthetic, only when `mock.scan` exists | profile sensors through `ros_gz_bridge` |
| Camera | not modelled | profile sensors through `ros_gz_bridge` |
| Truth | mock node publishes the label | `truth_publisher` publishes the label |
| Startup | nodes start directly | fail-closed: spawn → `startup_order`, each gated on exit 0 and a wall deadline |

The two backends do not share a command interface. A scenario that must run on
both needs a small adapter; this asymmetry is intentional (see ADR 0001 and
ROADMAP M5).

## 6. Assets kept outside git

The gate rejects `*.stl`, `*.dae`, `*.obj` and model weights anywhere in the
tree. Meshes therefore live outside the repository, for example under

```text
${JCHENG_ASSET_ROOT:-$HOME/.local/share/jcheng/assets}/<device>/
```

and `robot.yaml` points at the URDF by absolute path or `$JCHENG_ASSET_ROOT`.
The existing precedent is `docs/robots/piper_x/` (source manifest, joint map
and a fetch script). Licence rules from that manifest apply unchanged: adopt
MIT/Apache sources, require a LICENSE file, never copy an unlicensed asset.

## 7. Boundaries the engine keeps

- Domain 43 only; the launch refuses any other `domain_id`.
- `GZ_PARTITION=jcheng-sim` for every Gazebo run.
- `gz_ros2_control` and all controller nodes in `/sim`.
- No vendor topic (`/joint_states`, `/ros_robot_controller/*`) is published.
- No device is opened; no real motion is commanded.
- `/sim/joint_states` is plant state, never a bus measurement.

## 8. Related

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [SIMULATION_MODEL.md](SIMULATION_MODEL.md)
- [FAILURE_MODES.md](FAILURE_MODES.md)
- [ADR 0003](adr/0003-multi-robot-engine.md)
- [Piper X reference manifest](robots/piper_x/README.md) — not a plant yet
