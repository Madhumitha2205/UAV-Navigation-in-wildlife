"""Tests for independent route validator and safety integrity checks."""

import pytest
from backend.global_planner.environment import Environment, Waypoint
from backend.global_planner.route_validator import RouteValidator


@pytest.fixture
def base_env():
    env = Environment(
        x_min=0.0,
        x_max=100.0,
        y_min=0.0,
        y_max=100.0,
        start=Waypoint("start", 5.0, 5.0),
        destination=Waypoint("destination", 95.0, 95.0),
        safety_clearance=2.0,
        grid_resolution=1.0,
    )
    env.obstacle_manager.add_circular_obstacle("c1", 50.0, 50.0, 10.0)
    wps = [
        Waypoint("wp1", 20.0, 20.0),
        Waypoint("wp2", 80.0, 20.0),
        Waypoint("wp3", 80.0, 80.0),
    ]
    env.set_monitoring_waypoints(wps)
    return env


def test_valid_route_passes(base_env):
    validator = RouteValidator(base_env)
    wps = base_env.monitoring_waypoints

    # Clean path from start -> wp1 -> wp2 -> wp3 -> dest
    path_points = [
        (5.0, 5.0),
        (20.0, 20.0),
        (80.0, 20.0),
        (80.0, 80.0),
        (95.0, 95.0),
    ]
    report = validator.validate_route(ordered_waypoints=wps, path_points=path_points)
    assert report.is_valid is True
    assert len(report.errors) == 0
    assert report.details["collision_count"] == 0
    assert report.details["coverage_percentage"] == 100.0


def test_missing_mandatory_waypoint_fails(base_env):
    validator = RouteValidator(base_env)
    # Only visiting wp1 and wp2, missing wp3
    visited_wps = base_env.monitoring_waypoints[:2]
    path_points = [
        (5.0, 5.0),
        (20.0, 20.0),
        (80.0, 20.0),
        (95.0, 95.0),
    ]
    report = validator.validate_route(ordered_waypoints=visited_wps, path_points=path_points)
    assert report.is_valid is False
    assert any("Required mandatory waypoints not visited" in e for e in report.errors)


def test_wrong_destination_fails(base_env):
    validator = RouteValidator(base_env)
    wps = base_env.monitoring_waypoints
    path_points = [
        (5.0, 5.0),
        (20.0, 20.0),
        (80.0, 20.0),
        (80.0, 80.0),
        (50.0, 95.0),  # Wrong destination (expected 95, 95)
    ]
    report = validator.validate_route(ordered_waypoints=wps, path_points=path_points)
    assert report.is_valid is False
    assert any("does not match environment destination" in e for e in report.errors)


def test_obstacle_collision_fails(base_env):
    validator = RouteValidator(base_env)
    wps = base_env.monitoring_waypoints
    # Direct line cutting straight through obstacle at (50, 50) with radius 10
    path_points = [
        (5.0, 5.0),
        (20.0, 20.0),
        (80.0, 80.0),  # Segment from (20, 20) to (80, 80) passes right through (50, 50)!
        (80.0, 20.0),
        (95.0, 95.0),
    ]
    report = validator.validate_route(ordered_waypoints=wps, path_points=path_points)
    assert report.is_valid is False
    assert any("violates obstacle safety clearance" in e for e in report.errors)
    assert report.details["collision_count"] > 0


def test_out_of_bounds_point_fails(base_env):
    validator = RouteValidator(base_env)
    wps = base_env.monitoring_waypoints
    path_points = [
        (5.0, 5.0),
        (20.0, 20.0),
        (105.0, 20.0),  # Out of bounds!
        (80.0, 80.0),
        (95.0, 95.0),
    ]
    report = validator.validate_route(ordered_waypoints=wps, path_points=path_points)
    assert report.is_valid is False
    assert any("outside environment boundaries" in e for e in report.errors)
