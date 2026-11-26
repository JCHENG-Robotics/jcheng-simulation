"""Deterministic joint plant used by the mock backend.

This module is ROS-free so the core can be tested without a ROS installation.
The Gazebo backend uses the same limits from ``config/joint_limits.yaml``; the
two backends are intentionally not bit-identical (Gazebo integrates physics,
this plant integrates a first-order model). See docs/SIMULATION_MODEL.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

JOINT_ORDER = ("joint1", "joint2", "joint3", "joint4", "joint5", "r_joint")


@dataclass(frozen=True)
class JointLimit:
    """Commandable range and simulation velocity cap for one joint."""

    lower: float
    upper: float
    velocity: float

    def clamp(self, value: float) -> float:
        return min(max(float(value), self.lower), self.upper)


def load_joint_limits(path: str | Path) -> dict[str, JointLimit]:
    """Load and validate ``config/joint_limits.yaml``.

    The file must describe exactly :data:`JOINT_ORDER`; a missing or extra
    joint is an error rather than a silent default.
    """

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError(f"{path}: expected schema_version: 1")
    joints = data.get("joints")
    if not isinstance(joints, dict):
        raise ValueError(f"{path}: missing joints mapping")
    if set(joints) != set(JOINT_ORDER):
        raise ValueError(
            f"{path}: joints must be {list(JOINT_ORDER)}, got {sorted(joints)}"
        )

    limits: dict[str, JointLimit] = {}
    for name in JOINT_ORDER:
        entry = joints[name]
        try:
            lower = float(entry["lower"])
            upper = float(entry["upper"])
            velocity = float(entry["velocity"])
        except (KeyError, TypeError) as exc:
            raise ValueError(f"{path}: {name} needs lower/upper/velocity") from exc
        if not lower < upper:
            raise ValueError(f"{path}: {name} lower must be < upper")
        if velocity <= 0.0:
            raise ValueError(f"{path}: {name} velocity must be > 0")
        limits[name] = JointLimit(lower=lower, upper=upper, velocity=velocity)
    return limits


class JointPlant:
    """First-order, rate-limited joint model.

    Each step moves every joint toward its clamped target with a bounded
    velocity. The model is deterministic: the same target sequence and the same
    ``dt`` sequence produce the same state, with no randomness or wall clock.
    """

    def __init__(
        self,
        limits: Mapping[str, JointLimit],
        *,
        time_constant_s: float = 0.08,
        initial: Mapping[str, float] | None = None,
    ) -> None:
        missing = set(JOINT_ORDER) - set(limits)
        if missing:
            raise ValueError(f"missing joint limits: {sorted(missing)}")
        if time_constant_s <= 0.0:
            raise ValueError("time_constant_s must be > 0")

        self._limits = {name: limits[name] for name in JOINT_ORDER}
        self._time_constant_s = float(time_constant_s)
        start = initial or {}
        unknown = set(start) - set(JOINT_ORDER)
        if unknown:
            raise ValueError(f"unknown initial joints: {sorted(unknown)}")
        self._positions = {
            name: self._limits[name].clamp(start.get(name, 0.0)) for name in JOINT_ORDER
        }
        self._targets = dict(self._positions)
        self._velocities = {name: 0.0 for name in JOINT_ORDER}

    def set_targets(self, positions: Mapping[str, float]) -> None:
        """Set position targets. Unknown joint names are rejected."""

        unknown = set(positions) - set(JOINT_ORDER)
        if unknown:
            raise ValueError(f"unknown joints: {sorted(unknown)}")
        for name, value in positions.items():
            self._targets[name] = self._limits[name].clamp(value)

    def step(self, dt_s: float) -> dict[str, float]:
        """Advance the plant by ``dt_s`` seconds and return the new positions."""

        if not dt_s > 0.0:
            raise ValueError("dt_s must be > 0")
        for name in JOINT_ORDER:
            position = self._positions[name]
            target = self._targets[name]
            error = target - position
            if abs(error) < 1e-9:
                self._positions[name] = target
                self._velocities[name] = 0.0
                continue

            limit = self._limits[name]
            desired = error / self._time_constant_s
            velocity = min(max(desired, -limit.velocity), limit.velocity)
            delta = velocity * dt_s
            if abs(delta) >= abs(error):
                self._positions[name] = target
                self._velocities[name] = error / dt_s
            else:
                self._positions[name] = position + delta
                self._velocities[name] = velocity
        return self.positions

    @property
    def positions(self) -> dict[str, float]:
        return dict(self._positions)

    @property
    def targets(self) -> dict[str, float]:
        return dict(self._targets)

    @property
    def velocities(self) -> dict[str, float]:
        return dict(self._velocities)
