# Evidence — multi-robot engine (2026-11-26)

> Kind: offline simulation validation of the catalog engine.
> Host: operator laptop, ROS 2 Jazzy, Gazebo Sim 8.15.0 (`gz sim`),
> `gz_ros2_control` 1.2.20, `ros_gz_sim` 1.0.24, `controller_manager` 4.48.1,
> Python 3.12.3.
> Domain: 43. No hardware was opened, no robot was contacted, no real motion
> was commanded. These are **L2 offline simulation** results at most.

## 1. Build

```bash
colcon build --base-paths ros2_ws/src \
  --packages-select jcheng_simulation_robots \
                   jcheng_simulation_bringup \
                   jcheng_simulation_arm
```

Result: 3 packages finished, no errors. The install tree contains
`share/jcheng_simulation_robots/robots/{armpi_ultra,gate2_arm}/...` and the
`mock_plant` / `truth_publisher` console scripts.

## 2. Tests

```bash
# with ROS sourced
python3 -m pytest -q tests ros2_ws/src/jcheng_simulation_robots/test
# 85 passed

# bare Python (no ROS): the four launch-wiring cases skip by design
python3 -m pytest -q tests ros2_ws/src/jcheng_simulation_robots/test
# 81 passed, 4 skipped
```

The repository suite covers the contract, the catalog/profile schema, domain
isolation, the no-hardware scan, limits consistency for both robots, URDF
geometry, launch wiring and the documentation set. The engine package test
covers the strict controller-config resolver and the launch event wiring.

## 3. Catalog and launch arguments

```bash
bash scripts/check_repo_gate.sh
```

The gate's catalog step resolves every profile and every declared controller
profile:

```text
armpi_ultra: joints=['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'r_joint'] controller_profile=default sha256=8e1fc2d6d863
gate2_arm: joints=['joint1', 'joint2'] controller_profile=default sha256=b0c1ad43dbc4
gate2_arm: joints=['joint1', 'joint2'] controller_profile=gain_0p1 sha256=3016246edf65
gate2_arm: joints=['joint1', 'joint2'] controller_profile=gain_0p2 sha256=8b0c43656a4b
```

`ros2 launch jcheng_simulation_robots robot.launch.py --show-args` lists
`robot`, `backend`, `domain_id` (43), `headless`, `world`, `model_name`,
`controller_profile`, `controller_config`, `controller_manager`,
`startup_timeout`, `publish_truth`. `display.launch.py --show-args` lists
`robot`, `gui`, `domain_id`. The two compatibility wrappers resolve and show the
engine arguments.

## 4. `armpi_ultra` mock backend

```bash
ros2 launch jcheng_simulation_robots robot.launch.py \
  robot:=armpi_ultra backend:=mock
```

- `/sim/joint_states` was available after **1 s**.
- `/sim/truth/source` echoed `data: simulated`.
- `/sim/scan` had `header.frame_id: laser_link`, 360 ranges; the forward beam
  hit the obstacle at 0.65 m and the side walls at 1.5 m / 2.0 m.
- `ros2 topic pub --once /sim/joint_command ... {joint1: 0.5}` moved `joint1`
  to `0.5`; `r_joint` stayed at its profile initial `-0.4`.
- The node log recorded `mock plant ready: robot=armpi_ultra, 6 joints, 50 Hz
  step, 10 Hz scan`.

## 5. `gate2_arm` mock backend

```bash
ros2 launch jcheng_simulation_robots robot.launch.py \
  robot:=gate2_arm backend:=mock
```

- `/sim/joint_states` was available after **1 s** and carried exactly
  `['joint1', 'joint2']`.
- No `/sim/scan` topic existed (the profile declares no lidar).
- A `joint1` command of `0.4` was reached (`array('d', [0.4, 0.0])`).
- The node log recorded `mock plant ready: robot=gate2_arm, 2 joints, 50 Hz
  step`.

## 6. `gate2_arm` Gazebo backend

```bash
ros2 launch jcheng_simulation_robots robot.launch.py \
  robot:=gate2_arm backend:=gz headless:=true
```

- The action `/sim/arm_controller/follow_joint_trajectory` was available after
  **3 s**; nodes: `/jcheng_sim_truth`, `/robot_state_publisher`,
  `/ros_gz_bridge`, `/sim/arm_controller`, `/sim/controller_manager`,
  `/sim/gz_ros_control`, `/sim/joint_state_broadcaster`.
- `/sim/truth/source` echoed `data: simulated`.
- The launch log recorded the selection:
  `id=gate2_arm joints=['joint1', 'joint2'] controller_profile=default ...
  sha256=b0c1ad43...`.
- `FollowJointTrajectory` to `[0.3, -0.2]` in 3 s returned `error_code: 0`,
  `Goal successfully reached!`; `/sim/joint_states` read
  `array('d', [0.2999999999999977, -0.19999999999999873])`.
- Shutdown: `SIGTERM` to the launch, then the Gazebo server; no node remained
  on domain 43.

## 7. `armpi_ultra` Gazebo backend

```bash
ros2 launch jcheng_simulation_robots robot.launch.py \
  robot:=armpi_ultra backend:=gz headless:=true
```

- The launch waited for a free domain, then started; the action and both sensor
  topics were available after **5 s**, with exactly one `/clock` publisher.
- The launch log recorded
  `id=armpi_ultra joints=['joint1', …, 'r_joint'] controller_profile=default`.
- `FollowJointTrajectory` to `[0.3, 0.2, -0.2, 0.1, 0.0]` in 3 s returned
  `error_code: 0`, `Goal successfully reached!`.
- `/sim/joint_states` read
  `array('d', [0.2999999994691504, 0.19999999965517554, -0.19999999964024115,
  0.0999999998300019, -6.39e-13, -1.32e-21])` — the five arm joints at target,
  `r_joint` at 0.
- `/sim/scan` had `header.frame_id: laser_link`; `/sim/camera/camera_info`
  had `header.frame_id: camera_optical_frame`; `/sim/truth/source` echoed
  `data: simulated`.
- Shutdown: `SIGTERM` to the launch and the Gazebo server; the script's trap
  logged `cleanup done` and no node remained on domain 43.

This exercises the full profile path: three controllers in the fail-closed
chain (`joint_state_broadcaster` → `arm_controller` → `gripper_controller`), the
`ros_gz_bridge` lidar/camera mapping and a five-joint JTC goal.

## 8. Concurrency note

During this run, a separate session (`jcheng-research` Piper X experiment) was
repeatedly starting plants on domain 43 with `GZ_PARTITION=jcheng-sim` and a
`/clock` bridge. The ArmPi Gazebo verification waited for a free window
(20 s of polling in the successful run) rather than sharing the domain: two
plants collide on `/clock` and the controller manager. This is the documented
"one plant at a time" constraint, observed in practice. No foreign process was
stopped.

## 9. What this evidence does not support

- No hardware result (L5 is not applicable; this repository has no hardware
  path).
- No grasp, contact, payload or gripper claim for `gate2_arm` (two joints, no
  gripper); `armpi_ultra` has one finger and no grasp metric.
- No accuracy, repeatability or dynamic-identification claim; geometry and
  inertias are placeholders.
- No controller-level limit enforcement claim; `gz_ros2_control` logs that URDF
  command limits are ignored.
- The `gain_0p1` / `gain_0p2` profiles were validated as configuration and
  bytes, not characterized at runtime.
- GUI mode (`headless:=false`) was not exercised.

## 10. Compatibility wrapper smoke

The deprecated entry point still resolves and runs the engine:

```bash
ros2 launch jcheng_simulation_bringup sim.launch.py backend:=mock
```

The log recorded `mock plant ready: robot=armpi_ultra, 6 joints, 50 Hz step,
10 Hz scan`; `/sim/joint_states`, `/sim/scan`, `/sim/camera/image`,
`/sim/camera/camera_info` and `/sim/truth/source` (`data: simulated`) were
present. The launch tree was stopped afterwards.

The `/sim/scan` `ros2 topic echo` in this check printed a QoS fallback warning
because a foreign bridge from another session was also offering the topic on
domain 43; the engine's own scan check in §4 used a clean domain.

## 11. `piper_x` external-asset profile

The third catalog entry points at an MIT description kept outside git. This run
used the materialised bundle
`~/.local/share/jcheng/assets/piper_x/` (`JCHENG_ASSET_ROOT`) and the ament
prefix shim `<bundle>/prefix` that maps `agx_arm_description/agx_arm_urdf` to
the fetched URDF repository.

- Without `JCHENG_ASSET_ROOT` the gate reports
  `piper_x: ... model=unavailable (env JCHENG_ASSET_ROOT; asset prefix ...)`;
  the profile and its controller YAML still validate, and the launch refuses
  with the missing items.
- With the bundle, `xacro` expands the in-tree wrapper and the external
  description (301 lines, 12 joints) and `gz sdf -p` converts it. The engine
  inserts placeholder inertials for `world` and `gripper_link` (upstream omits
  them) and, per the profile, `<dynamics damping="1">` on the movable joints.
  The wrapper adds the `/sim` `ros2_control` block and the gz plugin; the
  upstream files are not modified.
- Mock backend: `mock plant ready: robot=piper_x, 7 joints, 50 Hz step`;
  `/sim/joint_states` carried `['joint1'…'joint6','gripper']`,
  `/sim/truth/source` echoed `simulated`, and a command of
  `joint1=0.3, gripper=0.05` settled at exactly those values.
- Gazebo backend: ready in **4 s**, controllers
  `joint_state_broadcaster`, `arm_controller`, `gripper_controller` active; the
  log selected `controller_profile=default gain=10.0` and the Piper
  controller YAML; the model is the upstream one (`Fixed joint
  ['world_to_base_link']`, `Loading joint: gripper`).
- `FollowJointTrajectory` to `[0.3, 0.3, -0.3, 0.2, 0.1, 0.0]` and the gripper
  goal to `[0.05]` both returned `error_code: 0`. The settled state was
  `[gripper 0.0544, joint1 0.2743, joint2 0.2634, joint3 -0.2986,
  joint4 0.2313, joint5 0.1052, joint6 -0.0131]`: a residual of up to ~0.04 rad
  under gravity. Tracking is **not characterised**; the plant is for
  wiring/interface validation.
- Limitations observed: Gazebo's physics engine does not support URDF mimic
  constraints (the two finger joints do not follow the master `gripper`); the
  headless DART build logs that some collision meshes could not be created, so
  contact/grasp fidelity is not claimed.

## 12. Related

- [README (repository)](../../README.md)
- [Multi-robot guide](../../docs/MULTI_ROBOT.md)
- [ADR 0003](../../docs/adr/0003-multi-robot-engine.md)
- [Earlier ArmPi validation](../20261126_offline_validation/README.md)
- [Earlier migrated-arm validation](../20261126_migrated_arm/README.md)
