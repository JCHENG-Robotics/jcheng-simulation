# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Multi-robot plant engine `jcheng_simulation_robots`: a `robot.yaml` catalog
  schema (`jcheng.simulation_robot.v1`), a generalized deterministic joint
  plant and scan model, a generic mock node, a Gazebo truth publisher and
  generic `robot.launch.py` / `display.launch.py` (ADR 0003).
- Robot catalog `robots/armpi_ultra/` and `robots/gate2_arm/`, each with a
  profile, text-only URDF, controller YAML, world and (ArmPi) sensor bridge.
  The migrated Gate-2 data keeps its MIT notice.
- `robots/piper_x/`: a catalog profile for the externally kept MIT Piper X
  description, an in-tree Gazebo wrapper that adds the `ros2_control` block,
  controller YAML (default `position_proportional_gain` 10) and a text-only
  world. The profile is catalogued without assets and launchable once
  `JCHENG_ASSET_ROOT` and the ament prefix exist.
- External-asset profiles: `model.requires_env`, `model.asset_prefix`,
  `model.joint_damping`, `controllers.default_gain`; the launch prepends the
  prefix to `AMENT_PREFIX_PATH`/`GZ_SIM_RESOURCE_PATH` and refuses a plant whose
  assets are missing. The fetch script now builds the
  `agx_arm_description` ament prefix shim.
- URDF normalisation (`jcheng_simulation_robots.model`): a 1 g placeholder
  inertial for geometry-less links and optional joint damping, applied in
  memory only; the external asset is never modified.
- Fail-closed staged startup for **every** Gazebo plant: `spawn` then the
  profile's `startup_order`, each stage gated on exit code 0 and a wall
  deadline; a support-process exit shuts the launch down.
- Gazebo backends now publish `/sim/truth/source` through `truth_publisher`
  (previously mock-only).
- `docs/MULTI_ROBOT.md` (schema and add-a-device guide),
  `docs/adr/0003-multi-robot-engine.md`, `tests/test_profiles.py`,
  `tests/test_urdf.py`, `tests/test_launch_wiring.py` and the engine package
  test `test/test_engine.py`.
- Offline evidence for the engine:
  `evidence/20261126_multi_robot_engine/README.md`.

### Changed

- `jcheng_simulation_bringup` and `jcheng_simulation_arm` are now thin
  compatibility wrappers that include the engine with a fixed robot id; their
  plant code, robot data and package tests moved into the engine/catalog.
- `scripts/check_repo_gate.sh` validates the whole catalog (every profile and
  controller profile) and scans all of `ros2_ws/src`; `simulation-ci` builds
  the three packages and smokes the engine's mock backend.
- `tests/test_limits_consistency.py`, `test_no_hardware.py`,
  `test_domain_isolation.py` and `test_plant.py` are parameterized by robot id
  or scan the whole source tree.
- `docs/robots/piper_x/README.md` points at the catalog as the way to add a
  device.

### Removed

- Per-package plant modules (`jcheng_simulation_bringup/`, the migrated
  `jcheng_simulation_arm/` implementation), `config/joint_limits.yaml`,
  `config/sim.yaml`, the duplicate URDF/world copies and
  `tests/test_arm_plant.py`; their content lives in the engine and the catalog.

## [0.1.0] — 2026-11-26

### Added

- Contract-compliant SIM repository skeleton: `capability.yaml` (class
  `offline`, domain 43), `VERSION`, four-document set, `LICENSE-REVIEW.md`,
  repository gate and `simulation-ci`.
- Deterministic mock plant: first-order joint model with vendor-derived
  position limits, 360-beam synthetic scan, `/sim/joint_command` setpoints,
  `/sim/joint_states`, `/sim/scan` and `/sim/truth/source=simulated`.
- Gazebo Harmonic backend: primitive-geometry ArmPi Ultra model, lab world,
  `gz_ros2_control` arm/gripper controllers, GPU lidar and wrist camera,
  `ros_gz_bridge` mapping and headless launch.
- Tests for the manifest contract, domain isolation, no-hardware boundary,
  joint/scan models, limits consistency and the documentation set.
- Offline validation evidence for the mock and Gazebo backends on
  Jazzy/Harmonic: `evidence/20261126_offline_validation/README.md`.
