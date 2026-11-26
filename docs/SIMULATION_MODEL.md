# Simulation model — jcheng-simulation

> Status: **provisional**, v0.1.0, 2026-11-26. Primitive geometry only.
> English canonical.

## 1. Scope of the model

The catalog currently holds two independent models:

- `armpi_ultra` (§2–§8): a fixed-base, 5-DoF arm with one gripper finger, a 2D
  LiDAR and a wrist camera. It exists to exercise graph wiring, message names,
  joint space motion, controllers and sensor consumers offline. It is **not** a
  geometric or dynamic replica of the ArmPi Ultra.
- `gate2_arm` (§9): a 2-DoF primitive arm migrated from the frozen baseline.
- `piper_x`: a 6-DoF arm with a parallel gripper whose description is the
  external MIT upstream model (not in git, not primitive). Its profile, wrapper
  and normalisation are documented in
  [docs/robots/piper_x/README.md](robots/piper_x/README.md); its numbers are
  not repeated here.

They are unrelated; do not transfer numbers between them. Each model is driven
by `robots/<id>/robot.yaml`; adding a device does not change this document's
structure, only the profile and its URDF (see
[MULTI_ROBOT.md](MULTI_ROBOT.md)).

No vendor mesh, vendor URDF file or vendor source is copied into this
repository. The vendor description in the frozen `jcheng-manipulation`
baseline was read only to keep joint names, axes and position limits aligned.

## 2. `armpi_ultra` joints

| Joint | Parent → child | Axis (URDF) | Lower (rad) | Upper (rad) | Sim velocity (rad/s) |
|---|---|---|---|---|---|
| `joint1` | `base_link` → `link1` | `0 0 1` | -1.8012 | 1.8012 | 1.5 |
| `joint2` | `link1` → `link2` | `0 -1 0` | -0.6618 | 1.1519 | 1.5 |
| `joint3` | `link2` → `link3` | `0 -1 0` | -1.8012 | 0.0 | 1.5 |
| `joint4` | `link3` → `link4` | `0 -1 0` | -1.5917 | 1.5917 | 1.5 |
| `joint5` | `link4` → `link5` | `0 0 -1` | -1.5917 | 1.5499 | 1.5 |
| `r_joint` | `gripper_link` → `r_link` | `1 0 0` | -2.22 | 0.0 | 1.5 |

Position limits are the vendor servo-EEPROM bounds minus the 20-pulse margin
adopted in the frozen baseline on 2026-11-18; the source path is
`jcheng-manipulation/ros2_ws/src/armpi_ultra_description/urdf/armpi_ultra.xacro`.
The velocity value is a **simulation command cap**, not a measured servo
limit; the vendor's `velocity="10"` and `effort="1000"` are placeholders. The
single source of truth is `robots/armpi_ultra/robot.yaml`; the URDF and the
controller YAML must agree, checked by `tests/test_limits_consistency.py`.

`l_joint` (the second finger, `mimic joint="r_joint" multiplier="-1"`) is
**not modeled** in v0.1. The model has one right finger; a grasp cannot close
on an object. This is a fidelity limitation, not a bug to work around.

## 3. Links and geometry (provisional)

| Link | Shape | Length / size (m) | Mass (kg) |
|---|---|---|---|
| `base_link` | box 0.14 × 0.14 × 0.06 | 0.06 high | 0.60 |
| `link1` | cylinder r 0.022 | 0.075 | 0.15 |
| `link2` | cylinder r 0.020 | 0.100 | 0.12 |
| `link3` | cylinder r 0.018 | 0.095 | 0.10 |
| `link4` | cylinder r 0.016 | 0.056 | 0.08 |
| `link5` | cylinder r 0.014 | 0.060 | 0.06 |
| `gripper_link` | box 0.03 × 0.05 × 0.03 | — | 0.03 |
| `r_link` | box 0.012 × 0.006 × 0.04 | — | 0.005 |
| `laser_link` | cylinder r 0.035 | 0.03 | 0.05 |
| `camera_link` | box 0.03 × 0.03 × 0.02 | — | 0.01 |

The arm is a straight vertical chain at zero pose. The camera is mounted on
`link4` with a nominal pitch of 0.8 rad and a REP-103 optical frame
(`camera_optical_frame`). The real camera extrinsic is not measured here.

## 4. Dynamics

### Mock backend

- First-order approach: `error / tau`, capped by the joint velocity limit,
  with `tau = 0.08 s` and a 50 Hz step.
- Targets are clamped to the YAML limits; the plant snaps to a target when the
  next step would cross it.
- No friction, gravity, backlash, torque limit, bus latency or collision.
- Deterministic for a fixed target and `dt` sequence.

### Gazebo backend

- Physics step 1 ms; `joint_trajectory_controller` configured at 100 Hz.
- Position commands only; no effort/current model.
- `gz_ros2_control` logs that command limits from the URDF are **ignored**
  ("Enforcing command limits is disabled"). The mock backend clamps; the
  Gazebo path relies on Gazebo joint limits and the controller's trajectory
  interpolation. Do not claim controller-level limit enforcement.
- Gazebo contact and friction are enabled, but no grasp or contact metric is
  validated in v0.1.

## 5. Sensors

| Sensor | Model | Rate | Parameters |
|---|---|---|---|
| LiDAR | `gpu_lidar` in Gazebo; raycast in mock | 10 Hz | 360 samples, -π…π, range 0.05–8.0 m, Gaussian σ 0.01 m, frame `laser_link` |
| Camera | Gazebo `camera` | 10 Hz | 640×480, R8G8B8, HFOV 1.2 rad, near 0.05, far 8.0, Gaussian σ 0.005, frame `camera_optical_frame`, `camera_info` topic |
| Depth | Not modeled | — | — |

The mock scan is a first-hit raycast against a 4.0 m × 3.0 m room with one
0.15 m-radius cylinder at `(0.8, 0.0)`; it has no noise, intensity, occlusion
or beam divergence. The Gazebo scan uses the sensor model above and the lab
world.

## 6. World

`worlds/jcheng_lab.sdf` is self-contained: no Fuel or network downloads.

- 10 m × 10 m ground plane, directional sun, Sensors/Physics/SceneBroadcaster
  system plugins.
- Table top 0.42 × 0.50 × 0.02 m at z = 0.25, on a 0.16 × 0.16 × 0.23 m
  pedestal, 0.30 m in front of the base.
- One 0.04 m red target cube at `(0.30, 0.0, 0.27)`.

The table height, cube pose and base placement are chosen for reach, not
measured from the real cell.

## 7. What this model can and cannot validate

| Can validate (offline) | Cannot validate |
|---|---|
| Topic/message names, frames and QoS wiring | Absolute accuracy or repeatability |
| Joint-space command → state consistency | Real servo dynamics, backlash, current, temperature |
| Controller activation and action semantics | Grasp success, contact forces, slip |
| Scan geometry and consumer plumbing | LiDAR accuracy, reflectivity, occlusion |
| Camera stream and camera_info plumbing | Camera calibration, depth alignment |
| Domain 43 isolation and launch guards | Hardware safety, e-stop, lease/deadman |
| Scenario timing at a coarse level | Real-time deadlines on the Pi 5 |

Synthetic, mock and Gazebo results are never hardware validation.

## 8. Determinism and reproducibility

- The mock backend is deterministic given the same target sequence and step
  sizes; it uses the wall clock for timestamps only.
- Gazebo is not bit-reproducible across hosts, renderers or versions. Record
  the Gazebo/`gz_ros2_control` versions with any evidence.
- The repository pins geometry and limits in text; there are no binary assets.

## 9. `gate2_arm` — migrated 2-DoF plant

`robots/gate2_arm/` is a second, independent model migrated from
the frozen baseline (`arm_description` at commit `a08b8b6`, see
[ADR 0002](adr/0002-second-plant-migrated-arm.md)). It is primitive geometry,
not the ArmPi Ultra; every adaptation is listed in
[MIGRATION-2026-11-26-baseline-arm.md](MIGRATION-2026-11-26-baseline-arm.md).

### Joints

| Joint | Parent → child | Axis | Lower (rad) | Upper (rad) | Limit effort | Limit velocity |
|---|---|---|---|---|---|---|
| `joint1` | `base_link` → `link1` | `0 0 1` | -3.14159 | 3.14159 | 100.0 | 3.0 |
| `joint2` | `link1` → `link2` | `0 0 1` | -3.14159 | 3.14159 | 50.0 | 3.0 |

Both joints are revolute about the local z axis. The angle, effort and velocity
values are copied unchanged from the baseline; they are **not** measured servo
limits and are not ArmPi Ultra values. The `<ros2_control>` command-interface
`min`/`max` equal the joint limits, checked by `tests/test_limits_consistency.py`.

### Links

| Link | Shape (m) | Mass (kg) |
|---|---|---|
| `base_link` | cylinder r 0.10, h 0.10 | 5.0 |
| `link1` | cylinder r 0.05, h 0.60 | 2.0 |
| `link2` | cylinder r 0.04, h 0.40 | 1.0 |

There is no gripper, no camera, no LiDAR and no mobile base.

### Dynamics and control

- Gazebo physics at a 1 ms step; `joint_trajectory_controller` at 100 Hz.
- `gz_ros2_control` runs in `/sim`; the action is
  `/sim/arm_controller/follow_joint_trajectory`.
- Three validated profiles (`config/arm_controllers*.yaml`): `default` (no gain
  override), `gain_0p1` and `gain_0p2` (`position_proportional_gain`). The two
  V2 files differ in that byte only.
- `gz_ros2_control` logs that URDF command limits are ignored; the caveat in §4
  applies. Do not claim controller-level limit enforcement.

### World

`worlds/arm_lab.sdf` is a 10 m × 10 m ground plane with a sun and the Physics,
SceneBroadcaster and UserCommands plugins. No Sensors plugin (the model has no
sensors), no Fuel download.

### What it validates and does not

| Can validate (offline) | Cannot validate |
|---|---|
| `ros2_control`/JTC wiring and action semantics | ArmPi Ultra geometry or dynamics |
| Controller-config schema, path resolution and provenance | Servo behavior, backlash, current, temperature |
| Fail-closed startup: stage exit codes and 60 s deadlines | Grasp, contact, payload |
| Domain-43 and `/sim` isolation for a second plant | Sensor or calibration claims |

## 10. Profiles are the source of truth

For every robot, `robots/<id>/robot.yaml` drives:

| Concern | Profile field |
|---|---|
| Command joints and limits | `joints` |
| Mock dynamics and hold time | `mock.rate_hz`, `mock.time_constant_s`, `mock.command_timeout_ms` |
| Mock scan | `mock.scan` (optional) |
| Controllers and spawn order | `controllers.items`, `controllers.startup_order` |
| Controller YAML and profiles | `controllers.config`, `controllers.profiles` |
| Sensor topics | `sensors`, `bridge.config` |
| Gazebo model, URDF, spawn pose | `model` |
| World | `world` |
| Topics and truth label | `topics`, `truth` |

The URDF and the controller YAML remain separate files because Gazebo consumes
them directly. `tests/test_limits_consistency.py` asserts that the profile, the
URDF and every controller profile agree on joints, bounds and interfaces, so a
drift is a gate failure rather than a silent mismatch.

## 11. Related

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [MULTI_ROBOT.md](MULTI_ROBOT.md)
- [FAILURE_MODES.md](FAILURE_MODES.md)
- [MIGRATION-2026-11-26-baseline-arm.md](MIGRATION-2026-11-26-baseline-arm.md)
- [ADR 0001](adr/0001-simulation-domain-and-truth.md)
- [ADR 0002](adr/0002-second-plant-migrated-arm.md)
- [ADR 0003](adr/0003-multi-robot-engine.md)
- [Piper X asset manifest](robots/piper_x/README.md) — reference only; not wired into any plant.
