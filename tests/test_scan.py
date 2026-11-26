"""Geometry tests for the synthetic scan model."""

import math

import pytest

from jcheng_simulation_bringup.scan import RoomModel, scan_ranges

ROOM = RoomModel(
    width_m=4.0,
    depth_m=3.0,
    obstacle_x_m=0.8,
    obstacle_y_m=0.0,
    obstacle_radius_m=0.15,
)


def test_forward_ray_hits_the_obstacle():
    assert ROOM.ray(0.0, 8.0) == pytest.approx(0.65, abs=1e-6)


def test_side_ray_hits_the_room_wall():
    assert ROOM.ray(math.pi / 2.0, 8.0) == pytest.approx(1.5, abs=1e-6)
    assert ROOM.ray(math.pi, 8.0) == pytest.approx(2.0, abs=1e-6)


def test_range_is_capped():
    assert ROOM.ray(0.0, 0.5) == pytest.approx(0.5, abs=1e-9)


def test_scan_has_the_requested_beam_count_and_bounds():
    ranges = scan_ranges(ROOM, 360, 8.0)
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
