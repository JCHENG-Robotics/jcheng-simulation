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
| Virtual plant, robot model, sensors, controllers and bridges | `jcheng-simulation` |

Keeping the plant in its own repository lets perception, mobile and system work
reuse the same simulated streams without importing the system test runner, and
gives the plant its own version, gate and evidence.

## 2. Domain isolation

| Control | Implementation |
|---|---|
| ROS domain | The launch sets `ROS_DOMAIN_ID` to the `domain_id` argument. `_validate_domain()` raises if the value is not `43`; no node is started. |
| Gazebo transport | The launch sets `GZ_PARTITION=jcheng-sim`, so a robot's Gazebo process on the same host cannot collide. |
| ROS namespace | Every plant **data** topic is `/clock` or starts with `/sim/`; standard ROS topics (`/tf`, `/tf_static`, `/rosout`, `/parameter_events`, `/robot_description`) also exist. |
| Vendor topics | No `/ros_robot_controller/*`, `/joint_states` (vendor name) or other vendor topic is published. |

Domain isolation is an **environment and naming** control, not a security
boundary. A malicious local process can still set `ROS_DOMAIN_ID=43`; SROS2 is
not enforced in v0.1. The plant never joins 0/41/42, and a capability process
that mistakenly joins 43 would see only simulated data, but the reverse
(malicious overrides) is out of scope.

## 3. Truth model

- The `/sim/` prefix is mandatory for plant data topics.
- `/sim/truth/source` is a transient-local `std_msgs/String` with the value
  `simulated`.
- `/sim/joint_states` is plant state. It resembles a measurement, but it is
  **not** a bus read and must never be compared with the robot's
  `GetBusServoState` as if both were measurements.
- Mock and Gazebo results are never reported as hardware validation, and no
  result here is an L5 result.

## 4. Backends

| Property | `backend:=mock` | `backend:=gz` |
|---|---|---|
| Runtime | ROS 2 only | ROS 2 Jazzy + Gazebo Harmonic |
| Joint input | `/sim/joint_command` `JointState` positions | `/sim/{arm,gripper}_controller/follow_joint_trajectory` actions |
| Joint state | `/sim/joint_states` at 50 Hz | `/sim/joint_states` from `joint_state_broadcaster` at 100 Hz |
| Plant dynamics | First-order, rate-limited, clamped | Gazebo physics + `joint_trajectory_controller` at 100 Hz |
| Scan | Synthetic raycast, 360 beams, 10 Hz | GPU lidar, 360 beams, 10 Hz |
| Camera | Not modeled | 640×480 camera, 10 Hz, nominal mount |
| Clock | Wall clock (`use_sim_time: false`) | Gazebo `/clock` (`use_sim_time: true`) |
| Determinism | Deterministic for a fixed target/dt sequence | Not bit-reproducible across hosts/versions |

The two backends do not share a command interface in v0.1. A scenario that must
work on both needs a small adapter (M5); this asymmetry is intentional and
documented rather than hidden behind a lowest-common-denominator API.

### Gazebo controller details

- `gz_ros2_control` places the controller_manager and controller nodes in the
  `/sim` namespace via the `<ros><namespace>/sim</namespace></ros>` block.
- The controller_manager subscribes to `robot_description`; the plugin remaps
  `robot_description:=/robot_description` so it receives the
  `robot_state_publisher` topic.
- The parameter file uses fully qualified node keys
  (`/sim/controller_manager`, `/sim/arm_controller`,
  `/sim/gripper_controller`). Unqualified keys are ignored and the spawner
  fails with "The 'type' param was not defined"; this was observed and fixed
  during the 2026-11-26 offline run.
- The controller_manager logs "Enforcing command limits is disabled. Command
  limits from URDF will be ignored." The URDF limits are therefore **not**
  enforced by ros2_control; Gazebo's own joint limits are the only physical
  bound. The mock backend does clamp. Do not claim controller-level limit
  enforcement on the Gazebo path.

## 5. Data flow

```text
mock backend
  test/scenario ──/sim/joint_command──> mock plant (first-order, clamped)
                                          ├──/sim/joint_states──> consumers
                                          ├──/sim/scan──────────> consumers
                                          └──/sim/truth/source──> consumers

Gazebo backend
  scenario ──FollowJointTrajectory──> /sim/arm_controller
                                      /sim/gripper_controller
                                            │ gz_ros2_control
                                            ▼
                                        Gazebo plant
                                          ├──/sim/joint_states (JTC + broadcaster)
                                          ├──/sim/scan (GPU lidar + bridge)
                                          ├──/sim/camera/image (camera + bridge)
                                          ├──/sim/camera/camera_info
                                          └──/clock
```

`robot_state_publisher` consumes `/sim/joint_states` and the URDF to publish
`/tf` and `/tf_static` on domain 43.

## 6. Failure semantics

| Condition | Behavior |
|---|---|
| `domain_id != 43` | Launch raises before starting any node. No fallback. |
| Gazebo missing or world invalid | Launch/Gazebo exits; no mock fallback. |
| Controller spawn fails | `spawner` exits non-zero; the launch log shows it; no silent substitution. |
| `robot_description` missing | The controller_manager waits and logs; controllers never activate. |
| Unknown joint in `/sim/joint_command` | The mock rejects the whole command and logs a throttled warning. |
| Command gap > 500 ms | The mock holds the last targets and logs once. |
| Sensor rendering failure | Gazebo logs the error; no fake scan/camera data is generated. |

There is no e-stop, no brake and no safety-rated stop in this repository; the
plant is a simulator.

## 7. Contract gap

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

## 8. Boundaries with other repositories

- **`jcheng-system`** owns `ExecuteMotion`, leases, deadman, the safety state
  machine, the vendor bridge and the real hardware. The plant never publishes a
  vendor topic and never calls the system API. `jcheng_testkit` may drive the
  plant on domain 43 in M5.
- **`jcheng-mobile`** consumes `/scan`; it can consume `/sim/scan` offline, but
  this repository does not depend on it and does not publish `/cmd_vel`.
- **`jcheng-perception`** consumes camera/depth/TF. v0.1 publishes a camera
  image and camera_info, but no depth stream; a wrist-camera model with a
  measured extrinsic is M4.
- **`jcheng-ops`** must not manage simulation processes as robot services.

## 9. Related

- [SIMULATION_MODEL.md](SIMULATION_MODEL.md)
- [FAILURE_MODES.md](FAILURE_MODES.md)
- [ADR 0001](adr/0001-simulation-domain-and-truth.md)
- [Repository taxonomy](https://github.com/JCHENG-Robotics/.github/blob/main/docs/repo-taxonomy.md)
