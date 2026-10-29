"""Tests for environment setup, coordinate validation, and bounds checking."""

import pytest
from backend.global_planner.config import EnvironmentConfig, Point3DConfig, CircularObstacleConfig, RectangularObstacleConfig
from backend.global_planner.environment import Environment, Waypoint


def test_valid_environment_initialization():
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
    env.add_monitoring_waypoint(Waypoint("wp1", 20.0, 20.0))

    errors = env.validate()
    assert errors == []
    assert env.is_inside_bounds(50.0, 50.0) is True
    assert env.is_inside_bounds(-1.0, 50.0) is False


def test_invalid_bounds():
    env = Environment(x_min=100.0, x_max=50.0, y_min=0.0, y_max=100.0)
    errors = env.validate()
    assert any("Invalid X bounds" in e for e in errors)


def test_start_destination_out_of_bounds():
    env = Environment(
        x_min=0.0,
        x_max=100.0,
        y_min=0.0,
        y_max=100.0,
        start=Waypoint("start", -5.0, 5.0),
        destination=Waypoint("destination", 105.0, 95.0),
    )
    errors = env.validate()
    assert any("Start" in e and "out of bounds" in e for e in errors)
    assert any("Destination" in e and "out of bounds" in e for e in errors)


def test_start_inside_obstacle_or_clearance():
    env = Environment(
        x_min=0.0,
        x_max=100.0,
        y_min=0.0,
        y_max=100.0,
        start=Waypoint("start", 10.0, 10.0),
        destination=Waypoint("destination", 95.0, 95.0),
        safety_clearance=2.0,
    )
    # Circle at (10, 10) with radius 5
    env.obstacle_manager.add_circular_obstacle("c1", 10.0, 10.0, 5.0)
    errors = env.validate()
    assert any("Start" in e and "collides with obstacle" in e for e in errors)


def test_waypoint_in_clearance_buffer():
    env = Environment(
        x_min=0.0,
        x_max=100.0,
        y_min=0.0,
        y_max=100.0,
        start=Waypoint("start", 5.0, 5.0),
        destination=Waypoint("destination", 95.0, 95.0),
        safety_clearance=3.0,
    )
    # Rect from [30, 40] x [30, 40], waypoint at (41, 35) is inside clearance buffer of 3m
    env.obstacle_manager.add_rectangular_obstacle("r1", 30.0, 40.0, 30.0, 40.0)
    env.add_monitoring_waypoint(Waypoint("wp_close", 41.0, 35.0))
    errors = env.validate()
    assert any("Waypoint wp_close" in e and "collides with obstacle/clearance buffer" in e for e in errors)


def test_duplicate_waypoint_ids():
    env = Environment(x_min=0.0, x_max=100.0, y_min=0.0, y_max=100.0)
    env.add_monitoring_waypoint(Waypoint("wp1", 20.0, 20.0))
    env.add_monitoring_waypoint(Waypoint("wp1", 40.0, 40.0))
    errors = env.validate()
    assert any("Duplicate waypoint ID: wp1" in e for e in errors)


def test_from_config_factory():
    cfg = EnvironmentConfig(
        x_min=0.0,
        x_max=50.0,
        y_min=0.0,
        y_max=50.0,
        start=Point3DConfig(x=2.0, y=2.0, altitude=12.0),
        destination=Point3DConfig(x=48.0, y=48.0, altitude=12.0),
        circular_obstacles=[CircularObstacleConfig(id="c1", x=25.0, y=25.0, radius=5.0)],
        rectangular_obstacles=[RectangularObstacleConfig(id="r1", x_min=10.0, x_max=15.0, y_min=10.0, y_max=15.0)],
    )
    env = Environment.from_config(cfg)
    assert env.start.x == 2.0
    assert env.destination.altitude == 12.0
    assert len(env.obstacle_manager.obstacles) == 2
    assert env.validate() == []
