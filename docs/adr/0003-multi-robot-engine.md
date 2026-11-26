# ADR 0003 — One multi-robot engine instead of one package per plant

> Status: **Accepted**, 2026-11-26. Unreleased (no VERSION bump).
> Partly supersedes ADR 0002 (the second-package split); the boundary decisions
> in ADR 0001 and ADR 0002 remain in force.
> English canonical.

## Context

ADR 0002 added the migrated Gate-2 arm as a second package,
`jcheng_simulation_arm`. That kept the ArmPi package's evidence untouched, but
it also established the wrong pattern for growth: every new device would copy
a package, a launch, a controller-config resolver, limit checks, gate entries
and tests. The owner expects **many different devices** (different arms, some
with grippers and sensors), so per-device packages would multiply the same
logic and drift between copies.

The repository also already contained a text-only robot manifest precedent
(`docs/robots/piper_x/`): geometry and joint data described in YAML, meshes
kept outside git, nothing loaded by a plant. That is the right shape for a
catalog.

## Decision

1. Introduce `jcheng_simulation_robots`, a single engine package:
   - a profile loader/validator (`jcheng.simulation_robot.v1`),
   - a generalized deterministic joint plant and scan model,
   - a generic mock node and a truth publisher,
   - a generic launch (`robot.launch.py robot:=<id> backend:=mock|gz`) with the
     fail-closed staged startup for both plants,
   - a generic display launch.
2. Move the robot data into the catalog: `robots/armpi_ultra/` and
   `robots/gate2_arm/`. The profile becomes the single source of truth for
   command joints, limits, controllers, sensor topics, world and mock
   behaviour; the old per-package `joint_limits.yaml`, `sim.yaml` and `controllers.yaml`
   duplicates disappear (controller YAML stays, because Gazebo needs it).
3. Keep `jcheng_simulation_bringup` and `jcheng_simulation_arm` as **thin
   compatibility entry points**. Their old launch commands still work and
   include the engine with a fixed robot id; they contain no plant code or
   robot data.
4. Extend the existing gate and tests rather than adding a per-robot gate:
   the catalog is validated for every profile, the boundary scan covers
   `ros2_ws/src`, and the limits/URDF/controller consistency test is
   parameterized by robot id.
5. Keep the asset policy: no mesh or model weight in git; external URDFs and
   meshes are referenced through an absolute path or `$JCHENG_ASSET_ROOT`.
6. Every Gazebo plant now uses the fail-closed staged startup (exit code 0 gates
   the next stage, per-stage wall deadline, support-process exit shuts the
   launch down). The ArmPi backend previously used fixed timers; this is a
   deliberate behavior improvement, re-verified offline.

## Consequences

Positive:

- A new device is one directory plus a `robot.yaml`; no Python or launch copy.
- One implementation of limits, controller selection, domain guard and startup
  semantics for every device.
- The two existing devices are migrated to the same path, so their evidence is
  comparable and the old commands still work through the wrappers.
- The Gazebo backends now publish `/sim/truth/source` (previously mock-only).
- The catalog can describe a device whose assets live outside git, which is
  the only viable route for vendor meshes under the current licence review.

Negative / accepted:

- A breaking layout change: code that imported `jcheng_simulation_bringup`
  modules or read the old `config/` paths must use the engine or the profile.
  The repository is Experimental and unreleased; the migration is recorded in
  CHANGELOG and the evidence is re-run.
- The profile now repeats joint limits that also exist in the URDF and the
  controller YAML. Tests enforce agreement; the repetition is the price of a
  machine-readable catalog.
- The fail-closed chain assumes `ros_gz_sim create` and the spawners are
  well-behaved; a hung stage is killed only by its launch deadline, not by a
  process signal.
- The engine is still single-plant-per-domain: two robots cannot run
  concurrently on domain 43 without namespace collisions.
- A profile with an external URDF fails to load when the asset bundle is not
  materialised. That is intentional (fail loud), but it means the catalog's
  gate cannot validate such a device on a bare host.

## Alternatives

| Alternative | Why not |
|---|---|
| Keep one package per device | Linear duplication of launch, resolver, gate and tests; drift across devices |
| Put everything in a single `jcheng_simulation_bringup` package | Keeps the verified package name but mixes two robots and grows without structure; the catalog is clearer |
| Generate URDF from the profile | Tempting for mesh-free primitives, but real devices arrive as URDF/xacro with meshes; generating one would still need a source-of-truth URDF |
| Load one profile per launch from a ros2 param file | Launch-time resolution of URDF/controller paths and validation is simpler in Python and testable without ROS |
| Delete the old packages outright | Breaks documented commands and the previous evidence trail; a thin wrapper costs ~40 lines |

## Related

- [ADR 0001](0001-simulation-domain-and-truth.md)
- [ADR 0002](0002-second-plant-migrated-arm.md)
- [MULTI_ROBOT.md](../MULTI_ROBOT.md) — schema and add-a-device guide
- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [MIGRATION-2026-11-26-baseline-arm.md](../MIGRATION-2026-11-26-baseline-arm.md)
