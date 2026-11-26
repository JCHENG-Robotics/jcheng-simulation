"""Deterministic joint plant used by the mock backend.

This module is ROS-free. Joint names and limits come from the robot profile, so
the same model drives any device in the catalog. The Gazebo backend integrates
real physics; the two backends are intentionally not bit-identical. See
``docs/SIMULATION_MODEL.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class JointLimit:
    """Commandable range and simulation velocity cap for one joint."""

    lower: float
    upper: float
    velocity: float

    def clamp(self, value: float) -> float:
        return min(max(float(value), self.lower), self.upper)


def validate_limits(limits: Mapping[str, JointLimit], joint_names: Iterable[str]) -> dict[str, JointLimit]:
    """Return the limits in ``joint_names`` order, rejecting gaps and nonsense."""

    names = tuple(joint_names)
    if not names:
        raise ValueError("joint_names must not be empty")
    if len(set(names)) != len(names):
        raise ValueError("joint_names contains duplicates")
    missing = set(names) - set(limits)
    if missing:
        raise ValueError(f"missing joint limits: {sorted(missing)}")
    extra = set(limits) - set(names)
    if extra:
        raise ValueError(f"limits for unknown joints: {sorted(extra)}")
    ordered: dict[str, JointLimit] = {}
    for name in names:
        limit = limits[name]
        if not limit.lower < limit.upper:
            raise ValueError(f"{name}: lower must be < upper")
        if limit.velocity <= 0.0:
            raise ValueError(f"{name}: velocity must be > 0")
        ordered[name] = limit
    return ordered


class JointPlant:
    """First-order, rate-limited joint model.

    Each step moves every joint toward its clamped target with a bounded
    velocity. The model is deterministic: the same target sequence and the same
    ``dt`` sequence produce the same state, with no randomness or wall clock.
    """

    def __init__(
        self,
        limits: Mapping[str, JointLimit],
        joint_names: Iterable[str],
        *,
        time_constant_s: float = 0.08,
        initial: Mapping[str, float] | None = None,
    ) -> None:
        self._joint_names = tuple(joint_names)
        self._limits = validate_limits(limits, self._joint_names)
        if time_constant_s <= 0.0:
            raise ValueError("time_constant_s must be > 0")
        self._time_constant_s = float(time_constant_s)
        start = initial or {}
        unknown = set(start) - set(self._joint_names)
        if unknown:
            raise ValueError(f"unknown initial joints: {sorted(unknown)}")
        self._positions = {
            name: self._limits[name].clamp(start.get(name, 0.0)) for name in self._joint_names
        }
        self._targets = dict(self._positions)
        self._velocities = {name: 0.0 for name in self._joint_names}

    @property
    def joint_names(self) -> tuple[str, ...]:
        return self._joint_names

    def set_targets(self, positions: Mapping[str, float]) -> None:
        """Set position targets. Unknown joint names are rejected."""

        unknown = set(positions) - set(self._joint_names)
        if unknown:
            raise ValueError(f"unknown joints: {sorted(unknown)}")
        for name, value in positions.items():
            self._targets[name] = self._limits[name].clamp(value)

    def step(self, dt_s: float) -> dict[str, float]:
        """Advance the plant by ``dt_s`` seconds and return the new positions."""

        if not dt_s > 0.0:
            raise ValueError("dt_s must be > 0")
        for name in self._joint_names:
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
