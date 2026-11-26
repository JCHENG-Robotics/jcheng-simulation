"""Geometry tests for the synthetic scan model."""

import math
from pathlib import Path

import pytest

from jcheng_simulation_robots.profile import load_catalog
from jcheng_simulation_robots.scan import RoomModel, scan_ranges

ROOT = Path(__file__).resolve().parents[1]
PROFILES = load_catalog(ROOT / "ros2_ws" / "src" / "jcheng_simulation_robots" / "robots")
SCAN = PROFILES["armpi_ultra"].mock.scan
ROOM = RoomModel.from_mapping(dict(SCAN.room))


def test_forward_ray_hits_the_obstacle():
    assert ROOM.ray(0.0, 8.0) == pytest.approx(0.65, abs=1e-6)


def test_side_ray_hits_the_room_wall():
    assert ROOM.ray(math.pi / 2.0, 8.0) == pytest.approx(1.5, abs=1e-6)
    assert ROOM.ray(math.pi, 8.0) == pytest.approx(2.0, abs=1e-6)


def test_range_is_capped():
    assert ROOM.ray(0.0, 0.5) == pytest.approx(0.5, abs=1e-9)


def test_scan_has_the_requested_beam_count_and_bounds():
    ranges = scan_ranges(ROOM, SCAN.beam_count, SCAN.max_range_m, angle_min_rad=SCAN.angle_min_rad, angle_max_rad=SCAN.angle_max_rad)
    assert len(ranges) == 360
    assert all(0.0 < value <= 8.0 for value in ranges)
    assert ranges[0] == pytest.approx(2.0, abs=1e-6)
    assert ranges[180] == pytest.approx(0.65, abs=1e-6)


def test_room_and_obstacle_validation():
    with pytest.raises(ValueError):
        RoomModel(0.0, 1.0, 0.1, 0.0, 0.1)
    with pytest.raises(ValueError):
        RoomModel(1.0, 1.0, 0.9, 0.0, 0.2)
    with pytest.raises(ValueError):
        scan_ranges(ROOM, 1, 8.0)
