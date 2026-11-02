"""Tests for obstacle-aware A* pathfinding and corner-cutting prevention."""

import math
import pytest
from backend.global_planner.environment import Environment, Waypoint
from backend.global_planner.grid_pathfinder import GridPathfinder


def test_open_space_path():
    env = Environment(
        x_min=0.0,
        x_max=50.0,
        y_min=0.0,
        y_max=50.0,
        start=Waypoint("start", 5.0, 5.0),
        destination=Waypoint("dest", 45.0, 45.0),
        safety_clearance=0.0,
        grid_resolution=1.0,
    )
    pathfinder = GridPathfinder(env)
    result = pathfinder.find_path((5.0, 5.0), (45.0, 45.0))

    assert result.success is True
    assert len(result.path_points) >= 2
    # Diagonal distance should be close to 40 * sqrt(2) ~= 56.57
    assert math.isclose(result.length, 40.0 * math.sqrt(2.0), rel_tol=0.05)


def test_obstacle_detour():
    env = Environment(
        x_min=0.0,
        x_max=50.0,
        y_min=0.0,
        y_max=50.0,
        start=Waypoint("start", 10.0, 25.0),
        destination=Waypoint("dest", 40.0, 25.0),
        safety_clearance=1.0,
        grid_resolution=1.0,
    )
    # Circular obstacle directly blocking straight line between (10, 25) and (40, 25)
    env.obstacle_manager.add_circular_obstacle("blocker", 25.0, 25.0, 8.0)

    pathfinder = GridPathfinder(env)
    result = pathfinder.find_path((10.0, 25.0), (40.0, 25.0))

    assert result.success is True
    # Path length must be strictly greater than straight line distance (30.0)
    assert result.length > 30.0

    # Ensure no point along the path collides with the obstacle + clearance
    for pt in result.path_points:
        assert env.obstacle_manager.point_collides(pt[0], pt[1], clearance=1.0) is False


def test_unreachable_target():
    env = Environment(
        x_min=0.0,
        x_max=50.0,
        y_min=0.0,
        y_max=50.0,
        start=Waypoint("start", 5.0, 5.0),
        destination=Waypoint("dest", 25.0, 25.0),
        safety_clearance=0.5,
        grid_resolution=1.0,
    )
    # Box completely enclosing (25, 25)
    # Walls on all four sides:
    env.obstacle_manager.add_rectangular_obstacle("wall_bottom", 20.0, 30.0, 18.0, 20.0)
    env.obstacle_manager.add_rectangular_obstacle("wall_top", 20.0, 30.0, 30.0, 32.0)
    env.obstacle_manager.add_rectangular_obstacle("wall_left", 18.0, 20.0, 18.0, 32.0)
    env.obstacle_manager.add_rectangular_obstacle("wall_right", 30.0, 32.0, 18.0, 32.0)

    pathfinder = GridPathfinder(env)
    result = pathfinder.find_path((5.0, 5.0), (25.0, 25.0))

    assert result.success is False
    assert result.length == float("inf")
    assert result.path_points == []


def test_no_corner_cutting():
    """Verify that diagonal movements cannot squeeze between diagonally adjacent obstacles."""
    env = Environment(
        x_min=0.0,
        x_max=10.0,
        y_min=0.0,
        y_max=10.0,
        start=Waypoint("start", 1.0, 1.0),
        destination=Waypoint("dest", 3.0, 3.0),
        safety_clearance=0.0,
        grid_resolution=1.0,
    )
    # Place obstacles at (2, 1) and (1, 2)
    # To move from (1, 1) to (2, 2) diagonally, corner cutting would cut through the junction
    env.obstacle_manager.add_rectangular_obstacle("obs1", 1.6, 2.4, 0.6, 1.4)
    env.obstacle_manager.add_rectangular_obstacle("obs2", 0.6, 1.4, 1.6, 2.4)

    pathfinder = GridPathfinder(env)
    # Verify cells (1, 2) and (2, 1) are occupied
    r1, c1 = pathfinder.world_to_grid(2.0, 1.0)
    r2, c2 = pathfinder.world_to_grid(1.0, 2.0)
    assert bool(pathfinder.occupancy[r1, c1]) is True
    assert bool(pathfinder.occupancy[r2, c2]) is True

    result = pathfinder.find_path((1.0, 1.0), (2.0, 2.0))
    # It must find an alternative detour route, not cut through the corner directly
    assert result.success is True
    # Straight diagonal length would be sqrt(2) ~= 1.414, detour must be longer
    assert result.length > 1.5


def test_coordinate_conversion_consistency():
    env = Environment(x_min=10.0, x_max=50.0, y_min=20.0, y_max=60.0, grid_resolution=0.5)
    pathfinder = GridPathfinder(env)

    row, col = pathfinder.world_to_grid(25.0, 35.0)
    wx, wy = pathfinder.grid_to_world(row, col)

    assert math.isclose(wx, 25.0, abs_tol=1e-5)
    assert math.isclose(wy, 35.0, abs_tol=1e-5)
