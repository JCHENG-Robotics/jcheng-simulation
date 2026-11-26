# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
