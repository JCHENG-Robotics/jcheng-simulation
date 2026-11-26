# Third-party notices — jcheng-simulation

This repository ships **no `LICENSE` file** while the organization license
review is open; see [LICENSE-REVIEW.md](LICENSE-REVIEW.md).

## Code migrated from the frozen `jcheng-manipulation` baseline

The Gate-2 arm data and the controller-config selection logic are derived from
project code in `jcheng-manipulation` (path `ros2_ws/src/arm_description`,
working tree at commit `a08b8b6`, 2026-11-26). That repository is licensed
under the MIT License:

```text
MIT License

Copyright (c) 2026 Kewei (Jericho) Cheng

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Derived files (current locations; the package `jcheng_simulation_arm` is now a
thin compatibility wrapper with no derived data):

| This repository | Baseline source |
|---|---|
| `ros2_ws/src/jcheng_simulation_robots/robots/gate2_arm/urdf/simple_arm.xacro` | `arm_description/urdf/simple_arm.xacro` |
| `ros2_ws/src/jcheng_simulation_robots/robots/gate2_arm/config/arm_controllers*.yaml` | `arm_description/config/arm_controllers*.yaml` |
| `ros2_ws/src/jcheng_simulation_robots/jcheng_simulation_robots/controller_config.py` | `arm_description/arm_description/controller_config.py` (generalized over the catalog) |
| `ros2_ws/src/jcheng_simulation_robots/launch/robot.launch.py` | `arm_description/launch/gazebo.launch.py` (generalized fail-closed chain) |
| `ros2_ws/src/jcheng_simulation_robots/test/test_engine.py` | `arm_description/test/test_controller_config.py` (ported) |

The modifications (namespace qualification, domain guard, catalog/profile
schema, generalized startup chain, rewritten display launch, new world) are
recorded in
[docs/MIGRATION-2026-11-26-baseline-arm.md](docs/MIGRATION-2026-11-26-baseline-arm.md)
and [ADR 0003](docs/adr/0003-multi-robot-engine.md). The MIT notice above is
retained because MIT requires it for copies and substantial portions; it does
not add a root `LICENSE` and does not decide the repository's own license.

## Vendor assets

**No vendor asset is present in this repository.** The vendor-derived ArmPi
Ultra meshes and URDF from `jcheng-manipulation` were deliberately **not**
migrated: `tests/test_no_hardware.py`, `scripts/check_repo_gate.sh` and the
model documentation forbid them. Every catalog URDF is text-only and
mesh-free.

A catalog profile may point at an external URDF or mesh bundle through an
absolute path or `$JCHENG_ASSET_ROOT`; those assets stay outside git and keep
their upstream licenses. See [docs/MULTI_ROBOT.md](docs/MULTI_ROBOT.md) §6 and
the Piper X manifest in [docs/robots/piper_x/](docs/robots/piper_x/README.md).

## External device descriptions (not vendored)

`robots/piper_x/` references the MIT Piper X description
(`agilexrobotics/agx_arm_urdf@680fa925cd00db7e2628563d2edc5540963045de`, see
[SOURCES.yaml](docs/robots/piper_x/SOURCES.yaml)) by path. The URDF and meshes
are **not** in this repository; the fetched bundle keeps its upstream `LICENSE`
files. The in-tree `urdf/piper_x_gz.urdf.xacro` is project code: it includes the
external file and adds the `ros2_control` block, and the engine's in-memory
normalisation (placeholder inertials, optional joint damping) does not modify
the asset.

## Runtime dependencies

The repository references, but does not vendor, ROS 2, Gazebo Sim,
`ros_gz`, `gz_ros2_control`, `controller_manager`, `robot_state_publisher`,
`xacro`, `rviz2` and their transitive dependencies. Each remains under its own
license.

## Reporting

If an attribution is wrong, open an issue with the path and the applicable
license.
