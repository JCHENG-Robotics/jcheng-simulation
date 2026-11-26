# Architecture — jcheng-simulation

> Status: **Experimental**, v0.1.0, 2026-11-26. Offline simulation only.
> English canonical.

## 1. Position in the ecosystem

`jcheng-simulation` is the **SIM layer**: an offline plant that stands in for
the vendor hardware world. It is deliberately outside the L0–L4 runtime
dependency graph in
[`repo-taxonomy.md`](https://github.com/JCHENG-Robotics/.github/blob/main/docs/repo-taxonomy.md):

- No runtime repository imports this one.
- This repository imports no L2/L3 runtime code; it only pins the
  `jcheng-interfaces` contract.
- It is not an L3 capability and never appears in the motion graph.

The ecosystem already assigns domain 43 to simulation; `jcheng-system`'s
`configs/domains.yaml` lists `jcheng_testkit` and mock vendor nodes as domain-43
members. The split is:

| Concern | Owner |
|---|---|
| Scenario definition, fault injection, pass/fail and report writing | `jcheng-system` / `jcheng_testkit` |
| Robot catalog, virtual plant, sensors, controllers and bridges | `jcheng-simulation` |

## 2. One engine, many robots

```text
robots/<id>/robot.yaml ──> profile loader/validator ──> generic launch
        │                         │                        │
        ├── urdf/*.xacro          │                        ├── backend:=mock
        ├── config/*.yaml         │                        └── backend:=gz
        ├── worlds/*.sdf          │
        └── bridge config         └── strict controller YAML selection
```

- `jcheng_simulation_robots` is the only plant implementation.
- `robots/<id>/` holds device data; the profile
  (`jcheng.simulation_robot.v1`) is the single source of truth for command
  joints, limits, controllers, sensor topics, world and mock behaviour.
- `launch/robot.launch.py robot:=<id>` builds either backend from the profile.
- `launch/display.launch.py robot:=<id> gui:=true` shows the model in RViz.

The schema, the add-a-device steps and the asset policy are in
[MULTI_ROBOT.md](MULTI_ROBOT.md). The layout decision is
[ADR 0003](adr/0003-multi-robot-engine.md).

## 3. Domain isolation

| Control | Implementation |
|---|---|
| ROS domain | Every engine launch sets `ROS_DOMAIN_ID` to the `domain_id` argument. `_validate_domain()` raises if the value is not `43`; no node is started. |
| Gazebo transport | The Gazebo launch sets `GZ_PARTITION=jcheng-sim`, so a robot's Gazebo process on the same host cannot collide. |
| ROS namespace | Every plant **data** topic is `/clock` or starts with `/sim/`; standard ROS topics (`/tf`, `/tf_static`, `/rosout`, `/parameter_events`, `/robot_description`) also exist. `gz_ros2_control` and the controller nodes live in `/sim`. |
| Vendor topics | No `/ros_robot_controller/*`, `/joint_states` (vendor name) or other vendor topic is published. |
| Per-domain exclusivity | One plant at a time: every robot claims `/sim/controller_manager` and its own controller actions. |

Domain isolation is an **environment and naming** control, not a security
boundary. A malicious local process can still set `ROS_DOMAIN_ID=43`; SROS2 is
not enforced in v0.1.

## 4. Truth model

- The `/sim/` prefix is mandatory for plant data topics.
- `/sim/truth/source` is a transient-local `std_msgs/String` with the profile's
  label (`simulated`). The mock node publishes it; `truth_publisher` publishes
  it for Gazebo backends.
- `/sim/joint_states` is plant state. It resembles a measurement, but it is
  **not** a bus read and must never be compared with the robot's
  `GetBusServoState` as if both were measurements.
- Mock and Gazebo results are never reported as hardware validation, and no
  result here is an L5 result.

## 5. Backends

| Property | `backend:=mock` | `backend:=gz` |
|---|---|---|
| Runtime | ROS 2 only | ROS 2 Jazzy + Gazebo Harmonic |
| Joint input | profile `joint_command` (`JointState` positions) | `<manager>/<controller>/follow_joint_trajectory` |
| Joint state | profile `joint_states` at `mock.rate_hz` | `joint_state_broadcaster` at the controller rate |
| Plant dynamics | First-order, rate-limited, clamped | Gazebo physics + `joint_trajectory_controller` |
| Scan | synthetic raycast, only when `mock.scan` exists | profile sensors through `ros_gz_bridge` |
| Camera | not modelled | profile sensors through `ros_gz_bridge` |
| Clock | wall clock (`use_sim_time: false`) | Gazebo `/clock` (`use_sim_time: true`) |
| Truth | mock node | `truth_publisher` |
| Determinism | deterministic for a fixed target/dt sequence | not bit-reproducible across hosts/versions |

The two backends do not share a command interface in v0.1. A scenario that must
work on both needs a small adapter (M5); this asymmetry is intentional and
documented rather than hidden behind a lowest-common-denominator API.

### Gazebo controller details

- `gz_ros2_control` places the controller_manager and controller nodes in the
  `/sim` namespace via the `<ros><namespace>/sim</namespace></ros>` block in
  each catalog URDF.
- The plugin remaps `robot_description:=/robot_description` so the
  controller_manager receives the `robot_state_publisher` topic.
- Controller YAML keys are fully qualified (`/sim/controller_manager`,
  `/sim/<controller>`). Unqualified keys are ignored by ROS 2 and the spawner
  fails with "The 'type' param was not defined"; the profile loader rejects
  them before Gazebo starts.
- The controller_manager logs "Enforcing command limits is disabled. Command
  limits from URDF will be ignored." The URDF limits are therefore **not**
  enforced by ros2_control; Gazebo's own joint limits are the only physical
  bound. The mock backend does clamp. Do not claim controller-level limit
  enforcement on the Gazebo path.
- A profile may declare a `gain_node` and named controller profiles (for
  example `gain_0p1`); the selected YAML must contain the declared
  `position_proportional_gain` as a float.

## 6. Startup and failure semantics

A Gazebo plant is **fail-closed**:

1. `spawn` starts 3 s after the launch so `robot_state_publisher` can publish
   `/robot_description`.
2. Each controller in the profile's `startup_order` starts only after the
   previous process exits 0.
3. Every stage has a wall deadline (`startup_timeout_s`, default 60 s); a
   missed deadline shuts the launch down naming the stage.
4. `robot_state_publisher`, the `/clock` bridge or the sensor bridge exiting
   shuts the launch down; there is no silent fallback.

The fail-closed chain is shared by every robot. The ArmPi backend used fixed
8 s/12 s timers in v0.1; it now uses the same chain (re-verified offline).

## 7. Data flow

```text
mock backend
  scenario ──<profile joint_command>──> generic mock plant
                                          ├──<profile joint_states>──> consumers
                                          ├──<profile scan>─────────> consumers (if declared)
                                          └──<profile truth>────────> consumers

Gazebo backend
  scenario ──FollowJointTrajectory──> /sim/<controller>
                                            │ gz_ros2_control
                                            ▼
                                        Gazebo plant
                                          ├──/sim/joint_states (JTC + broadcaster)
                                          ├──/sim/<sensor topics> (bridge)
                                          ├──/clock
                                          └──/sim/truth/source
```

## 8. Contract gap

`capability-manifest.v1` (interfaces v0.1.0) has:

- `runtime.ros_domains.items.const = 42`
- `safety.requires_lease.const = true`

An offline plant cannot satisfy both. This repository writes
`ros_domains: [43]` and `requires_lease: false`, and
`tests/test_contract.py` asserts the deviation explicitly. The runtime
`CapabilityManifest.msg` is not derived from this file because the plant is
never registered as a capability. The proper fix is an interfaces revision
(M3 in [ROADMAP](../ROADMAP.md)); until then, do not "correct" the values
silently.

## 9. Boundaries with other repositories

- **`jcheng-system`** owns `ExecuteMotion`, leases, deadman, the safety state
  machine, the vendor bridge and the real hardware. The plant never publishes a
  vendor topic and never calls the system API. `jcheng_testkit` may drive the
  plant on domain 43 in M5.
- **`jcheng-mobile`** consumes `/scan`; it can consume a simulated scan offline,
  but this repository does not depend on it and does not publish `/cmd_vel`.
- **`jcheng-perception`** consumes camera/depth/TF. The ArmPi profile publishes
  a camera image and camera_info, but no depth stream; a wrist-camera model with
  a measured extrinsic is M4.
- **`jcheng-ops`** must not manage simulation processes as robot services.
- **`jcheng-research`** may run its own experiments on domain 43; run one plant
  at a time and check `ros2 node list` before starting a plant.

## 10. Compatibility entry points

`jcheng_simulation_bringup` and `jcheng_simulation_arm` are thin ament_cmake
packages. Their launch files include the engine with a fixed robot id:

| Old command | Now |
|---|---|
| `ros2 launch jcheng_simulation_bringup sim.launch.py backend:=mock` | engine `robot:=armpi_ultra` |
| `ros2 launch jcheng_simulation_arm gazebo.launch.py` | engine `robot:=gate2_arm backend:=gz` |
| `ros2 launch jcheng_simulation_arm display.launch.py` | engine `display.launch.py robot:=gate2_arm` |

They contain no plant code or robot data and can be removed once external
scripts and recorded commands no longer reference them.

## 11. Related

- [MULTI_ROBOT.md](MULTI_ROBOT.md)
- [SIMULATION_MODEL.md](SIMULATION_MODEL.md)
- [FAILURE_MODES.md](FAILURE_MODES.md)
- [ADR 0001](adr/0001-simulation-domain-and-truth.md)
- [ADR 0003](adr/0003-multi-robot-engine.md)
- [Repository taxonomy](https://github.com/JCHENG-Robotics/.github/blob/main/docs/repo-taxonomy.md)
