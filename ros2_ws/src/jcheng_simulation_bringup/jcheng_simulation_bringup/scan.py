"""Synthetic 2D scan model for the mock backend.

The room is a rectangle centred on the plant origin with one circular
obstacle. This is a geometry model, not a sensor simulation: it has no noise,
no intensity, no occlusion beyond the first hit, and no beam divergence. The
Gazebo backend uses a real GPU lidar sensor instead.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RoomModel:
    width_m: float
    depth_m: float
    obstacle_x_m: float
    obstacle_y_m: float
    obstacle_radius_m: float

    def __post_init__(self) -> None:
        if self.width_m <= 0.0 or self.depth_m <= 0.0:
            raise ValueError("room dimensions must be > 0")
        if self.obstacle_radius_m <= 0.0:
            raise ValueError("obstacle radius must be > 0")
        if abs(self.obstacle_x_m) + self.obstacle_radius_m >= self.width_m / 2.0:
            raise ValueError("obstacle must be fully inside the room in x")
        if abs(self.obstacle_y_m) + self.obstacle_radius_m >= self.depth_m / 2.0:
            raise ValueError("obstacle must be fully inside the room in y")

    def ray(self, angle_rad: float, max_range_m: float) -> float:
        """Return the nearest hit distance for a ray from the origin."""

        if max_range_m <= 0.0:
            raise ValueError("max_range_m must be > 0")
        dx = math.cos(angle_rad)
        dy = math.sin(angle_rad)
        half_w = self.width_m / 2.0
        half_d = self.depth_m / 2.0

        wall = math.inf
        if dx > 1e-12:
            wall = min(wall, half_w / dx)
        elif dx < -1e-12:
            wall = min(wall, -half_w / dx)
        if dy > 1e-12:
            wall = min(wall, half_d / dy)
        elif dy < -1e-12:
            wall = min(wall, -half_d / dy)

        obstacle = math.inf
        # |o + t d - c|^2 = r^2 with o = (0, 0)
        ox = -self.obstacle_x_m
        oy = -self.obstacle_y_m
        b = 2.0 * (ox * dx + oy * dy)
        c = ox * ox + oy * oy - self.obstacle_radius_m**2
        discriminant = b * b - 4.0 * c
        if discriminant >= 0.0:
            root = math.sqrt(discriminant)
            candidates = [(-b - root) / 2.0, (-b + root) / 2.0]
            positive = [t for t in candidates if t > 1e-9]
            if positive:
                obstacle = min(positive)

        hit = min(wall, obstacle)
        return float(min(hit, max_range_m))


def scan_ranges(
    room: RoomModel,
    beam_count: int,
    max_range_m: float,
    *,
    angle_min_rad: float = -math.pi,
    angle_max_rad: float = math.pi,
) -> list[float]:
    """Return ``beam_count`` ranges from ``angle_min`` to ``angle_max``."""

    if beam_count < 2:
        raise ValueError("beam_count must be >= 2")
    step = (angle_max_rad - angle_min_rad) / beam_count
    return [
        room.ray(angle_min_rad + index * step, max_range_m)
        for index in range(beam_count)
    ]
