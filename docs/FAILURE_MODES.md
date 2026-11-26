# Failure modes — jcheng-simulation

> Status: **v0.1.0**, 2026-11-26. English canonical.

This document lists the failure modes that matter for an offline plant. None of
them is a hardware safety mechanism; the simulator has no e-stop.

## 1. Domain or namespace leak

| Failure | Effect | Detection | Mitigation |
|---|---|---|---|
| `domain_id` set to 0/41/42 | Simulated data appears in a robot graph, or the plant sees real vendor data | Launch raises before starting; `tests/test_domain_isolation.py` scans source/config | Never override `domain_id`; keep topic names `/sim/*`; set `GZ_PARTITION=jcheng-sim` |
| A ROS topic loses the `/sim` prefix | A consumer mistakes simulated data for a real stream | `tests/test_domain_isolation.py` and the gate scan raw topic literals | Add the prefix at the publisher; do not alias vendor names |
| Gazebo partition collision | Two Gazebo servers share topics/entities | `gz topic -l` shows unexpected topics or duplicate models | Keep `GZ_PARTITION` unique; use one server per host |

Domain isolation is environment-based. It is not an SROS2 security boundary;
a malicious local process can join domain 43.

## 2. Simulation mistaken for hardware

| Failure | Effect | Detection | Mitigation |
|---|---|---|---|
| A mock/Gazebo result is quoted as hardware evidence | False verification claim | `/sim/truth/source=simulated`; evidence path; ACCEPTANCE L-levels | Never report L2 as L5; keep the truth topic |
| A `/sim/joint_states` value is treated as a bus measurement | Wrong calibration/accuracy conclusion | Source topic and frame review | State explicitly that plant state is not `GetBusServoState` |
| A Gazebo camera image is used to tune perception thresholds | Overfitting to a synthetic renderer | Source topic review | Keep simulated and hardware datasets separate |

## 3. Catalog, profile and launch failures

| Failure | Effect | Detection | Mitigation |
|---|---|---|---|
| Unknown `robot:=` id | Nothing starts | Launch lists the catalog and raises | Use a directory under `robots/` |
| Profile schema error (bad joint, missing controller coverage, dup id) | Nothing starts | `load_profile` raises; the gate loads every profile | Fix the profile; `docs/MULTI_ROBOT.md` is the schema |
| URDF or world missing | Nothing starts | Profile loader names the resolved path | Keep the file in the robot directory or point at `$JCHENG_ASSET_ROOT` |
| Profile with sensors but no `bridge.config` | Nothing starts | Profile loader raises | Add the `ros_gz_bridge` mapping |
| Sensor/mock scan disagreement | Nothing starts | `mock.scan` must match a lidar `ros_topic`/`frame` | Keep the two in sync |
| Unqualified controller YAML keys | `spawner` fails with "The 'type' param was not defined" | Resolver rejects the file before launch | Keep `/sim/...` keys; the resolver logs path and SHA-256 |
| Controller YAML schema drift | Nothing starts | Resolver compares against the profile exactly | Update the profile and the YAML together |
| Wrong `controller_profile` name | Nothing starts | Resolver lists the allowed profiles | Use `default` or a name under `controllers.profiles` |
| Gazebo/ROS processes from an earlier run | Duplicate nodes, stale topics, ports/actions collide | `ros2 node list` shows two managers or two `robot_state_publisher` | Run one plant per domain; stop the whole process group and verify with `ps` |
| Both catalog robots launched together | Duplicate `/sim/controller_manager` and `/sim/arm_controller` | Two managers on domain 43 | Run one plant at a time |

## 4. Gazebo bringup failures (observed)

| Failure | Effect | Detection | Mitigation |
|---|---|---|---|
| `robot_description` remapping missing | controller_manager waits forever; controllers never activate | `sim.controller_manager` logs "will wait for the robot description" | Keep `<remapping>robot_description:=/robot_description</remapping>` |
| Controller spawner runs before the manager | `list_controllers` service not available | Spawner logs waiting; then fails | The engine starts each spawner only after `spawn` exits 0 and uses `--controller-manager-timeout 55` |
| Headless rendering unavailable | `libEGL warning: egl: failed to create dri2 screen`; sensors may fail | Gazebo log; no sensor topics | Sensors still published in the 2026-11-26 runs; treat the warning as unverified rendering and check the topics |
| `gz_ros2_control` command limits disabled | Commands are not clamped by ros2_control | Explicit controller_manager log line | Do not claim controller-level limits; mock clamps, Gazebo relies on physics limits |
| Startup stage exits non-zero | The next stage does not start; the launch shuts down | Log line `plant launch failure: stage=…` | Fix the failing stage; do not bypass the chain |
| Stage misses its wall deadline | Shutdown naming the stage; no partial plant | `wall deadline exceeded (…)` | Check Gazebo/controller_manager logs; restart cleanly |
| `robot_state_publisher`, `/clock` or sensor bridge exits | Whole launch shuts down | `returncode=…` shutdown message | Treat as a bringup failure; no mock fallback |
| Display launched on a non-43 domain | Simulated robot TF could appear in a robot graph | Launch raises `RuntimeError` | Keep `domain_id:=43`; never override |

## 5. Mock plant failures

| Failure | Effect | Detection | Mitigation |
|---|---|---|---|
| Command names/positions length mismatch | Command ignored | Throttled warning | Send `JointState.name` and `position` with equal length |
| Unknown joint name | Whole command rejected | Throttled warning with the offending name | Use the profile's joint names |
| No command for > 500 ms | Last targets are held (not a stop) | One-time info log | This is a simulator hold; do not model it as a safety stop |
| `use_sim_time` set without a `/clock` publisher | Timers stall; no state/scan | No topics after startup | The mock is a wall-clock backend; use `use_sim_time: false` |
| Wall-clock timestamp mixed into a sim-time bag | Time jumps; replay breaks | Bag inspection | Keep mock and Gazebo recordings separate |

## 6. Resource and DDS failures

| Failure | Effect | Detection | Mitigation |
|---|---|---|---|
| CPU saturation (Gazebo + perception on one host) | DDS reader wedges, dropped scans, delayed services | Missing topics, `ros2 topic hz`, host load | Run the plant and the perception GPU stack on separate hosts, or reduce rates |
| Dead DDS participant | A reader stops updating while other topics continue | Per-topic rate check | Restart the owning process; a retry loop is not a fix |
| Mixed RMW implementations | Services silently unavailable | `ros2 service list`/call failures | One RMW per graph; match the environment |

## 7. Physical and safety limits

The simulator has no e-stop, brake, bumper or safety-rated stop. It cannot
validate any of them. The real platform also has no hardware e-stop; the
software stop in `jcheng-system` is not an e-stop. Never infer a safety claim
from a simulation run.

## 8. Vendor assets and licensing

| Failure | Effect | Detection | Mitigation |
|---|---|---|---|
| Copying vendor meshes/URDF into this repository | License and provenance problem | Gate asset scan; review | Keep in-tree URDFs primitive; point an external profile at an asset bundle under `$JCHENG_ASSET_ROOT` |
| Adding model weights to the tree | Repository bloat and license ambiguity | Gate asset scan | Keep weights outside the repository (`/opt/jcheng/models/`) |
| Adding a `LICENSE` before the review closes | Conflicts with organization policy | Gate required-file check | Leave `LICENSE-REVIEW.md` as the record |
| External asset bundle missing | The profile fails to load; no plant starts | Error names the resolved path | Materialise the bundle (see `docs/robots/piper_x/`) or keep a text-only stand-in |

## 9. Related

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [MULTI_ROBOT.md](MULTI_ROBOT.md)
- [SIMULATION_MODEL.md](SIMULATION_MODEL.md)
- [Evidence 2026-11-26](../evidence/20261126_offline_validation/README.md)
