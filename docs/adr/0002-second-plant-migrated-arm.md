# ADR 0002 — Second plant: a migrated 2-DoF arm in the same SIM repository

> Status: **Accepted**, 2026-11-26. Unreleased (no VERSION bump).
> **Partly superseded by [ADR 0003](0003-multi-robot-engine.md) later the same
> day:** the package split described here was replaced by one multi-robot engine
> plus a catalog. The boundary, provenance and licensing decisions remain in
> force, and the Gate-2 data now lives in `robots/gate2_arm/`.
> English canonical.

## Context

ADR 0001 created a single-plant repository: one primitive ArmPi Ultra plant
with a mock backend and a Gazebo Harmonic backend. The documentation said so
explicitly, and `docs/robots/piper_x/README.md` recorded that a second plant
would need an ADR, a gate update and matching tests.

The frozen `jcheng-manipulation` baseline (`v1.0.0`) carries a Gate-2 Gazebo
bringup for a 2-DoF primitive arm. It is not a manipulation capability: it
exists to prove `ros2_control` wiring, strict controller-config selection and a
fail-closed staged startup chain — mechanisms the ArmPi plant does not have.
It is project code (MIT), contains no mesh and no vendor token, and the
baseline is frozen, so keeping it only there means keeping a live mechanism in
an archived tree.

## Decision

1. Copy the baseline's `arm_description` package into this repository as
   `ros2_ws/src/jcheng_simulation_arm/`, adapted to the domain-43 and `/sim`
   boundaries. The baseline is **not** modified and nothing is deleted from it.
2. Keep it as a **second, independent package** rather than folding it into
   `jcheng_simulation_bringup`: the existing package's verified v0.1 evidence
   must stay valid, and the two plants have different command surfaces.
3. Apply the same boundary rules as the first plant: `domain_id` 43 enforced by
   the launch, `GZ_PARTITION=jcheng-sim`, `gz_ros2_control` in `/sim`, no
   un-namespaced `/joint_states` or `/controller_manager`, no device access,
   no mesh, no vendor asset.
4. Extend the gate and tests instead of creating a parallel gate:
   `scripts/check_repo_gate.sh` scans both packages; `tests/test_no_hardware.py`
   and `tests/test_domain_isolation.py` cover both; `tests/test_arm_plant.py`
   covers the new model; the package keeps its own resolver/launch-wiring test.
5. Record provenance, the disposition of every baseline simulation-related
   path, and the MIT notice in
   [MIGRATION-2026-11-26-baseline-arm.md](../MIGRATION-2026-11-26-baseline-arm.md)
   and [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).
6. Run **one plant at a time**: both expose `/sim/controller_manager` and
   `/sim/arm_controller`. This is a documented constraint, not a shared-instance
   design.

## Consequences

Positive:

- The fail-closed startup and controller-config machinery stay in a maintained,
  testable repository instead of a frozen baseline.
- The first plant's evidence, tests and files are unchanged; the second plant
  has its own package test and offline evidence.
- The repository proves that a second plant can be added under the existing
  boundaries with a text-only model.

Negative / accepted:

- Two plants, two command surfaces and two evidence sets; the repository is no
  longer described as single-plant.
- The new plant's model is unrelated to the ArmPi Ultra (2 revolute joints,
  ±3.14159 rad, no gripper, no sensors), so its numbers must never be quoted as
  ArmPi geometry.
- The two plants cannot run simultaneously on one domain without colliding.
- Gate and test surface grew; both packages must be kept in the boundary scans.
- The package carries MIT-derived code while the repository has no `LICENSE`;
  the MIT notice is retained in `THIRD_PARTY_NOTICES.md`, and the repository's
  own license remains pending.

## Alternatives

| Alternative | Why not |
|---|---|
| Leave the bringup only in `jcheng-manipulation` | The baseline is frozen; a live mechanism there will not be maintained or tested against the current gate |
| Move (delete from the baseline) | Breaks the frozen baseline's CI, evidence links and tag contents |
| Merge into `jcheng_simulation_bringup` | Mixes two robots and two command surfaces, and perturbs the verified v0.1 package |
| Copy the vendor `armpi_ultra_description` instead | Vendor meshes/URDF are forbidden by the gate, the tests and the license review |
| Copy the whole baseline simulation surface (MoveIt, mock grasp, measurement simulate) | Out of scope: MoveIt planning and grasp mocks are not plants; evidence stays with the baseline chain |

## Related

- [ADR 0001](0001-simulation-domain-and-truth.md)
- [Migration record](../MIGRATION-2026-11-26-baseline-arm.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [SIMULATION_MODEL.md](../SIMULATION_MODEL.md)
- [Third-party notices](../../THIRD_PARTY_NOTICES.md)
