# Evidence — migrated 2-DoF arm plant (2026-11-26)

> Layout note (added later on 2026-11-26): this run used the temporary
> `jcheng_simulation_arm` package. The same data now lives in
> `ros2_ws/src/jcheng_simulation_robots/robots/gate2_arm/` and the launch is
> `robot.launch.py robot:=gate2_arm`; the re-run under the engine is
> [evidence/20261126_multi_robot_engine](../20261126_multi_robot_engine/README.md).
> The package still exists as a thin compatibility wrapper.

> Kind: offline simulation validation of the migrated Gate-2 arm plant.
> Host: operator laptop, ROS 2 Jazzy, Gazebo Sim 8.15.0 (`gz sim`),
> `gz_ros2_control` 1.2.20, `ros_gz_sim` 1.0.24, `controller_manager` 4.48.1,
> Python 3.12.3.
> Domain: 43. No hardware was opened, no robot was contacted, no real motion
> was commanded. These are **L2 offline simulation** results at most.

## 1. Build

```bash
colcon build --base-paths ros2_ws/src --packages-select jcheng_simulation_arm
```

Result: 1 package finished, no errors. The install tree contains
`share/jcheng_simulation_arm/{urdf,launch,config,worlds}` and the installed
Python module.

## 2. Package tests

```bash
# with ROS sourced
python3 -m pytest -q ros2_ws/src/jcheng_simulation_arm/test
# 9 passed

# with a bare Python (no ROS): the launch-wiring cases skip by design
python3 -m pytest -q ros2_ws/src/jcheng_simulation_arm/test
# 4 passed, 5 skipped
```

The four always-on tests cover the strict controller-config resolver (profile
allow-list, schema, YAML feature rejection, path handling). The five launch
tests need `launch`, `launch_ros`, `ament_index_python` and `xacro`.

## 3. Model and world

```bash
xacro ros2_ws/src/jcheng_simulation_arm/urdf/simple_arm.xacro > /tmp/jcheng_sim_arm.urdf
gz sdf -p /tmp/jcheng_sim_arm.urdf > /tmp/jcheng_sim_arm.sdf
gz sdf -p ros2_ws/src/jcheng_simulation_arm/worlds/arm_lab.sdf > /tmp/jcheng_arm_lab.sdf
```

| Output | Result |
|---|---|
| Expanded URDF | 166 lines |
| Robot SDF | 181 lines, contains the `gz_ros2_control` plugin with `<namespace>/sim</namespace>`, the `robot_description:=/robot_description` remapping and the selected controller YAML |
| World SDF | 68 lines, `Physics` + `SceneBroadcaster` + `UserCommands`, no `Sensors` plugin |

`gz sdf -p` printed three `[parser_urdf.cc:1220] Attribute value string not
set` warnings. They come from the empty `<ode/>` blocks that URDF→SDF
generates for the cylinder surfaces; the conversion succeeds and the model
loads. They are not a missing field in `simple_arm.xacro`.

## 4. Launch descriptions

```bash
ros2 launch jcheng_simulation_arm gazebo.launch.py --show-args
ros2 launch jcheng_simulation_arm display.launch.py --show-args
```

`gazebo.launch.py` exposes `controller_profile` (default|gain_0p1|gain_0p2),
`controller_config`, `domain_id` (default 43), `world`, `model_name`
(default `jcheng_sim_arm`) and `headless` (default true).
`display.launch.py` exposes `gui` (default false) and `domain_id` (default 43).

## 5. Headless end-to-end

```bash
export ROS_DOMAIN_ID=43
ros2 launch jcheng_simulation_arm gazebo.launch.py headless:=true
```

The launch log records the validated controller selection:

```text
arm controller config selected: profile=default input='' \
  realpath=.../share/jcheng_simulation_arm/config/arm_controllers.yaml \
  sha256=b0c1ad43dbc4d46d0e553034e4c47ec50ed64e945bef5b0065fb2e78fe7c730e
```

The action was available after **3 s** of wall time. Node list on domain 43:

```text
/robot_state_publisher
/ros_gz_bridge
/sim/arm_controller
/sim/controller_manager
/sim/gz_ros_control
/sim/joint_state_broadcaster
```

Action: `/sim/arm_controller/follow_joint_trajectory`
[control_msgs/action/FollowJointTrajectory].

Topic list on domain 43 (plant topics):

```text
/clock
/sim/arm_controller/controller_state
/sim/arm_controller/joint_trajectory
/sim/arm_controller/speed_scaling_input
/sim/arm_controller/transition_event
/sim/controller_manager/activity
/sim/dynamic_joint_states
/sim/joint_state_broadcaster/transition_event
/sim/joint_states
```

There is no un-namespaced `/joint_states` or `/controller_manager` on the
domain.

### Simulated trajectory

```bash
ros2 action send_goal /sim/arm_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  "{trajectory: {joint_names: [joint1, joint2],
     points: [{positions: [0.3, -0.2],
               time_from_start: {sec: 3, nanosec: 0}}]}}"
```

Result:

```text
Goal accepted with ID: e7050433c4ea4f4a9b6938d96943bbec

Result:
    error_code: 0
error_string: Goal successfully reached!

Goal finished with status: SUCCEEDED
```

`/sim/joint_states` afterwards:

```text
name: ['joint1', 'joint2']
position: [0.29999999999999755, -0.19999999999999865]
```

`ros2 topic echo` printed two `A message was lost!!!` notices while reading a
100 Hz `joint_states` stream with a depth-1 subscription. They are a reader-QoS
artifact, not a plant gap; the trajectory result and the final state agree.

### Shutdown

The launch session was terminated with `SIGTERM`. The Gazebo server, launch
process and controller nodes were gone within 2 s; no process remained.

## 6. Repository gate

```bash
bash scripts/check_repo_gate.sh
# 53 passed, 5 skipped   (the 5 skips are the launch-wiring tests without ROS)
# gate OK
```

## 7. What this evidence does not support

- No hardware result (L5 is not applicable; this repository has no hardware path).
- No grasp, contact, payload or gripper claim: the model has two joints and no
  gripper.
- No accuracy, repeatability or dynamic-identification claim; geometry and
  inertias are placeholders.
- No controller-level limit enforcement claim; `gz_ros2_control` logs that URDF
  command limits are ignored.
- The `gain_0p1` and `gain_0p2` profiles were validated as configuration and
  bytes, not characterized at runtime.
- GUI mode (`headless:=false`) was not exercised on this host.

## 8. Related

- [README (repository)](../../README.md)
- [Migration record](../../docs/MIGRATION-2026-11-26-baseline-arm.md)
- [Simulation model](../../docs/SIMULATION_MODEL.md)
- [Offline validation of the v0.1 plant](../20261126_offline_validation/README.md)
