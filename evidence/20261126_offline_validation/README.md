# 2026-11-26 — offline validation (jcheng-simulation)

> Layout note (added later on 2026-11-26): this run used the original
> single-package layout (`jcheng_simulation_bringup/config`, `urdf`, `worlds`)
> and the timer-based Gazebo startup. The robot data now lives in
> `ros2_ws/src/jcheng_simulation_robots/robots/armpi_ultra/` and the startup is
> the fail-closed chain; the re-run under the engine is
> [evidence/20261126_multi_robot_engine](../20261126_multi_robot_engine/README.md).

Status: **pass, offline simulation only.** No hardware was accessed and no
hardware motion was commanded. Operator: JerichoCheng.

Scope: contract and boundary gates, URDF/world validation, the deterministic
mock backend, the Gazebo Harmonic backend, and one simulated arm trajectory.
This is an L0/L1/L2 bundle; it is not L5 evidence.

## Environment

| Item | Value |
|---|---|
| Host | Operator laptop, Linux 7.0.0-43-generic x86_64 |
| Python | 3.12.3 |
| ROS | Jazzy (`/opt/ros/jazzy`) |
| Gazebo Sim | 8.15.0 (Harmonic) |
| `ros_gz` | 1.0.24 |
| `gz_ros2_control` | 1.2.20 |
| `joint_trajectory_controller` | 4.42.1 |
| Robot | **Not used.** No Pi, no vendor container, no bus servo. |

## 1. Unit, contract and boundary tests

Command:

```bash
python3 -m pytest -q tests
```

Result: **37 passed** (contract, domain isolation, no-hardware scan, joint
plant, scan model, limits consistency, documentation set).

## 2. Repository gate

Command:

```bash
bash scripts/check_repo_gate.sh
```

Result: **gate OK** (required files, Python syntax, XML parsing, no-hardware
and domain-43 scans, no vendor assets, tests, relative doc links).

## 3. URDF and world

```bash
xacro ros2_ws/src/jcheng_simulation_bringup/urdf/jcheng_armpi_sim.urdf.xacro \
  controllers_yaml:=$PWD/ros2_ws/src/jcheng_simulation_bringup/config/controllers.yaml \
  > /tmp/jcheng_armpi_sim.urdf
gz sdf -p /tmp/jcheng_armpi_sim.urdf > /tmp/jcheng_armpi_sim.sdf
gz sdf -p ros2_ws/src/jcheng_simulation_bringup/worlds/jcheng_lab.sdf \
  > /tmp/jcheng_lab.sdf
```

Result: xacro output 447 lines; converted robot SDF 589 lines; world SDF 159
lines; both conversions exited 0.

Warnings observed (non-fatal): `parser_urdf.cc: Attribute value string not set`
(×6), and sdformat copied the sensor extension elements `gz_frame_id` and
`camera_info_topic` as unknown children. Gazebo consumed them at runtime.

## 4. Build and launch description

```bash
colcon build --base-paths ros2_ws/src --packages-select jcheng_simulation_bringup
source install/setup.bash
ros2 launch jcheng_simulation_bringup sim.launch.py --show-args
```

Result: build finished; the launch exposed `backend` (mock/gz), `domain_id`
(43), `world`, `model_name`, `headless` (true), and `controller_manager`
(`/sim/controller_manager`).

## 5. Mock backend (L2)

```bash
ROS_DOMAIN_ID=43 ros2 launch jcheng_simulation_bringup sim.launch.py backend:=mock
```

Observed topics: `/sim/joint_command`, `/sim/joint_states`, `/sim/scan`,
`/sim/truth/source`. `/sim/truth/source` echoed `data: simulated`.

`/sim/scan` metadata: `frame_id: laser_link`, `angle_min -3.14159`,
`angle_max 3.14159`, `angle_increment 0.0174533`, `range_min 0.05`,
`range_max 8.0`, `scan_time 0.1`.

Command:

```bash
ros2 topic pub --once /sim/joint_command sensor_msgs/msg/JointState \
  "{name: ['joint1','r_joint'], position: [0.5,-1.0]}"
```

Result after one second: `/sim/joint_states` positions `joint1 = 0.5`,
`r_joint = -1.0`; the plant clamped, rate-limited and settled as expected. A
500 ms command gap then logged the hold message.

## 6. Gazebo backend (L2, headless)

```bash
ROS_DOMAIN_ID=43 ros2 launch jcheng_simulation_bringup sim.launch.py \
  backend:=gz headless:=true
```

Result: the controller_manager received `/robot_description`, the hardware
`JchengSimSystem` initialized, and `/sim/joint_states` appeared about 8 s after
launch (simulation stamp 6.842 s). Controllers present:

```text
/sim/arm_controller/follow_joint_trajectory
/sim/gripper_controller/follow_joint_trajectory
```

Topics present: `/clock`, `/sim/joint_states`, `/sim/scan`,
`/sim/camera/image`, `/sim/camera/camera_info`, `/sim/dynamic_joint_states`,
`/tf`, `/tf_static`. Scan frame `laser_link`; the first scan stamp was 8.2 s.

Trajectory goal:

```bash
ros2 action send_goal /sim/arm_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  "{trajectory: {joint_names: [joint1,joint2,joint3,joint4,joint5],
     points: [{positions: [0.3,0.2,-0.2,0.1,0.0],
               time_from_start: {sec: 2, nanosec: 0}}]}}"
```

Result: goal accepted, `error_code: 0`, `error_string: Goal successfully
reached!`, status `SUCCEEDED`. The next `/sim/joint_states` sample reported
`0.29999999, 0.19999999, -0.19999999, 0.09999999, -6.4e-13`, matching the
requested point.

The log also contains `libEGL warning: egl: failed to create dri2 screen` and
the controller_manager warning "Enforcing command limits is disabled. Command
limits from URDF will be ignored." Both are recorded in
[FAILURE_MODES.md](../../docs/FAILURE_MODES.md); sensors still published.

## 7. What this evidence does not show

- No hardware access, no real arm motion, no bus-servo read.
- No geometric accuracy, calibration or repeatability claim.
- No grasp or contact-force claim (the model has one gripper finger).
- No mobile base, Nav2, depth camera or external camera.
- No robot-bound Humble timing or Pi 5 resource claim.
- Gazebo results are not reproducible bit-for-bit across hosts.

## 8. Reproduction notes

- Stop the whole launch process group; killing only the launcher can leave
  `robot_state_publisher`, `ros_gz_bridge` and `gz sim` alive. During
  development this produced duplicate nodes and stale discovery entries.
- Use one Gazebo server per host and keep `GZ_PARTITION=jcheng-sim`.
- The Gazebo path needs the `robot_description` remapping and fully qualified
  controller parameter keys described in
  [ARCHITECTURE.md](../../docs/ARCHITECTURE.md).

## 9. Related

- [README](../../README.md)
- [ACCEPTANCE](../../ACCEPTANCE.md)
- [ARCHITECTURE](../../docs/ARCHITECTURE.md)
