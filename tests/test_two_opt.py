"""Tests for 2-Opt local search trajectory optimization."""

import pytest
from backend.global_planner.config import TwoOptConfig
from backend.global_planner.environment import Environment, Waypoint
from backend.global_planner.fitness import RouteFitnessCalculator
from backend.global_planner.grid_pathfinder import GridPathfinder
from backend.global_planner.two_opt import TwoOptOptimizer


def test_two_opt_untangles_crossing_route():
    """Deterministic test: Start at (0, 0), Dest at (100, 0).

    Waypoints placed on a line or square:
    wp0: (25, 25)
    wp1: (75, -25)
    wp2: (25, -25)
    wp3: (75, 25)

    A crossed order [0, 1, 2, 3] creates crossing paths between (25, 25)->(75, -25)
    and (25, -25)->(75, 25).
    2-Opt must reverse the crossed subsequence to eliminate the criss-cross,
    significantly reducing total path length.
    """
    env = Environment(
        x_min=-50.0,
        x_max=150.0,
        y_min=-50.0,
        y_max=50.0,
        start=Waypoint("start", 0.0, 0.0),
        destination=Waypoint("dest", 100.0, 0.0),
        safety_clearance=0.0,
        grid_resolution=1.0,
    )
    wps = [
        Waypoint("wp0", 25.0, 25.0),
        Waypoint("wp1", 75.0, -25.0),
        Waypoint("wp2", 25.0, -25.0),
        Waypoint("wp3", 75.0, 25.0),
    ]
    env.set_monitoring_waypoints(wps)

    pathfinder = GridPathfinder(env)
    calculator = RouteFitnessCalculator(env, pathfinder, wps)
    optimizer = TwoOptOptimizer(calculator, TwoOptConfig(max_iterations=50))

    crossed_chromosome = [0, 1, 2, 3]
    initial_cost, initial_feasible, _ = calculator.evaluate_chromosome(crossed_chromosome)
    assert initial_feasible is True

    optimized_chromosome, final_cost, was_improved = optimizer.optimize(crossed_chromosome)

    assert was_improved is True
    assert final_cost < initial_cost - 5.0
    # Must preserve exact set of waypoints
    assert sorted(optimized_chromosome) == [0, 1, 2, 3]
    # Check that route is still feasible
    _, final_feasible, _ = calculator.evaluate_chromosome(optimized_chromosome)
    assert final_feasible is True


def test_two_opt_rejects_infeasible_swap():
    """Test that 2-Opt never accepts a candidate that causes an obstacle collision."""
    env = Environment(
        x_min=0.0,
        x_max=100.0,
        y_min=0.0,
        y_max=100.0,
        start=Waypoint("start", 5.0, 50.0),
        destination=Waypoint("dest", 95.0, 50.0),
        safety_clearance=1.0,
        grid_resolution=1.0,
    )
    # Put a large wall blocking vertical transit across the middle
    env.obstacle_manager.add_rectangular_obstacle("wall", 45.0, 55.0, 20.0, 80.0)

    wps = [
        Waypoint("wp0", 20.0, 80.0),
        Waypoint("wp1", 30.0, 80.0),
        Waypoint("wp2", 70.0, 80.0),
        Waypoint("wp3", 80.0, 80.0),
    ]
    env.set_monitoring_waypoints(wps)

    pathfinder = GridPathfinder(env)
    calculator = RouteFitnessCalculator(env, pathfinder, wps)
    optimizer = TwoOptOptimizer(calculator)

    initial_route = [0, 1, 2, 3]
    opt_route, opt_cost, _ = optimizer.optimize(initial_route)

    # Whatever route 2-Opt returns must be strictly feasible
    _, is_feasible, _ = calculator.evaluate_chromosome(opt_route)
    assert is_feasible is True
    assert sorted(opt_route) == [0, 1, 2, 3]
