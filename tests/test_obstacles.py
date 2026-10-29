"""Tests for obstacle geometry, collision detection, and clearance buffers."""

import math
import pytest
from backend.global_planner.obstacle_manager import (
    CircularObstacle,
    RectangularObstacle,
    ObstacleManager,
)


def test_circular_obstacle_point_collision():
    obs = CircularObstacle("circle_1", x=50.0, y=50.0, radius=10.0)

    # Point at center (inside)
    assert obs.point_collides(50.0, 50.0, clearance=0.0) is True

    # Point at radius 8 (inside)
    assert obs.point_collides(58.0, 50.0, clearance=0.0) is True

    # Point at radius 10 (on boundary)
    assert obs.point_collides(60.0, 50.0, clearance=0.0) is True

    # Point at radius 11 (outside without clearance)
    assert obs.point_collides(61.0, 50.0, clearance=0.0) is False

    # Point at radius 11 (inside with clearance=2.0)
    assert obs.point_collides(61.0, 50.0, clearance=2.0) is True

    # Point at radius 13 (outside with clearance=2.0)
    assert obs.point_collides(63.0, 50.0, clearance=2.0) is False


def test_circular_obstacle_segment_collision():
    obs = CircularObstacle("circle_1", x=50.0, y=50.0, radius=10.0)

    # Segment passing straight through center
    assert obs.segment_collides((30.0, 50.0), (70.0, 50.0), clearance=0.0) is True

    # Segment passing at y=61 (missing obstacle with clearance 0)
    assert obs.segment_collides((30.0, 61.0), (70.0, 61.0), clearance=0.0) is False

    # Segment passing at y=61 with clearance=2.0 (effective radius 12.0 -> collides)
    assert obs.segment_collides((30.0, 61.0), (70.0, 61.0), clearance=2.0) is True

    # Segment passing at y=65 with clearance=2.0 (safe)
    assert obs.segment_collides((30.0, 65.0), (70.0, 65.0), clearance=2.0) is False


def test_rectangular_obstacle_point_collision():
    obs = RectangularObstacle("rect_1", x_min=20.0, x_max=40.0, y_min=20.0, y_max=40.0)

    # Center
    assert obs.point_collides(30.0, 30.0, clearance=0.0) is True

    # Outside by 1 meter
    assert obs.point_collides(41.0, 30.0, clearance=0.0) is False

    # Within clearance buffer
    assert obs.point_collides(41.0, 30.0, clearance=2.0) is True

    # Beyond clearance buffer
    assert obs.point_collides(43.0, 30.0, clearance=2.0) is False


def test_rectangular_obstacle_segment_collision():
    obs = RectangularObstacle("rect_1", x_min=20.0, x_max=40.0, y_min=20.0, y_max=40.0)

    # Segment crossing through the box
    assert obs.segment_collides((10.0, 30.0), (50.0, 30.0), clearance=0.0) is True

    # Segment grazing top edge at y=41 (misses with clearance 0)
    assert obs.segment_collides((10.0, 41.0), (50.0, 41.0), clearance=0.0) is False

    # Segment grazing top edge at y=41 with clearance 2 (collides)
    assert obs.segment_collides((10.0, 41.0), (50.0, 41.0), clearance=2.0) is True

    # Segment safely passing at y=45 with clearance 2 (misses)
    assert obs.segment_collides((10.0, 45.0), (50.0, 45.0), clearance=2.0) is False


def test_obstacle_manager_rasterization():
    mgr = ObstacleManager(default_clearance=2.0)
    mgr.add_circular_obstacle("c1", 50.0, 50.0, 10.0)

    grid, w, h = mgr.rasterize_grid(
        x_min=0.0, x_max=100.0, y_min=0.0, y_max=100.0, grid_resolution=1.0, clearance=2.0
    )

    assert grid.shape == (101, 101)
    # Center (50, 50) must be occupied
    assert bool(grid[50, 50]) is True
    # Point at (50, 61) is dist 11 <= 10 + 2 = 12 -> occupied
    assert bool(grid[61, 50]) is True
    # Point at (50, 65) is dist 15 > 12 -> free
    assert bool(grid[65, 50]) is False
    # Origin (0, 0) must be free
    assert bool(grid[0, 0]) is False
