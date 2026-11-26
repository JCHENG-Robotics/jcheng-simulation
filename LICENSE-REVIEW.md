# License review — jcheng-simulation

> Status: **pending** as of 2026-11-26.
> This repository deliberately ships **no `LICENSE`** while the organization
> license review is open, matching `jcheng-interfaces`, `jcheng-system`,
> `jcheng-perception`, `jcheng-ops` and `.github`.

## 1. Current facts

| Item | Fact |
|---|---|
| `LICENSE` file | Absent by design |
| Organization policy | `.github/docs/license-review.md` — no `LICENSE` in the new repositories until the review is approved |
| Exception | `jcheng-mobile` retains an MIT `LICENSE` added at initialization; `jcheng-manipulation` is the frozen MIT baseline |

## 2. Third-party inventory (to verify)

| Dependency | Use | Known/probable license | Risk |
|---|---|---|---|
| ROS 2 Jazzy | Simulation host | Apache-2.0 | Low; keep notices |
| Gazebo Sim (Harmonic) | Physics and sensors | Apache-2.0 | Low |
| `ros_gz` / `ros_gz_bridge` | ROS ↔ Gazebo transport | Apache-2.0 | Low |
| `gz_ros2_control` | Simulated controllers | Apache-2.0 | Low |
| `joint_state_broadcaster`, `joint_trajectory_controller` | Controllers | Apache-2.0 / BSD-3-Clause | Low |
| CycloneDDS | DDS (if enabled) | EPL-2.0 / EDL | Medium if distributed in an image |
| Vendor ArmPi Ultra meshes and URDF | **Not in this repository** | Vendor | Loaded read-only from the vendor workspace when needed; primitive geometry is used otherwise |

No model weights, vendor meshes or vendor source files are part of this
repository.

## 3. Open questions

- [ ] Confirm the ecosystem-wide license decision before v1.0.
- [ ] Decide whether simulation assets that derive from vendor geometry need a
      separate notice when they are eventually added.
- [x] Decide whether a `THIRD_PARTY_NOTICES.md` is required for a published
      simulation image. **Added 2026-11-26** for the MIT-derived Gate-2 code;
      it does not add a root `LICENSE` and does not decide the repository's own
      license.

## 4. Related

- [`.github/docs/license-review.md`](https://github.com/JCHENG-Robotics/.github/blob/main/docs/license-review.md)
- [Acceptance report](ACCEPTANCE.md)
- [README](README.md)
