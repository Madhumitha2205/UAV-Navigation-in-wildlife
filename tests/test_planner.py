"""Integration tests for Genetic Algorithm, Planner Service, and AirSim export."""

import json
from pathlib import Path
import pytest

from backend.global_planner.config import PlannerConfig, GeneticAlgorithmConfig
from backend.global_planner.environment import Environment, Waypoint
from backend.global_planner.fitness import RouteFitnessCalculator
from backend.global_planner.genetic_algorithm import GeneticAlgorithm
from backend.global_planner.grid_pathfinder import GridPathfinder
from backend.global_planner.planner_service import GlobalPlannerService, PlannedRoute


def test_ga_permutation_validity():
    """Verify that OX crossover and mutation always produce valid permutations."""
    env = Environment(x_min=0.0, x_max=50.0, y_min=0.0, y_max=50.0)
    wps = [Waypoint(f"wp{i}", float(i * 5), float(i * 5)) for i in range(8)]
    env.set_monitoring_waypoints(wps)

    pathfinder = GridPathfinder(env)
    calculator = RouteFitnessCalculator(env, pathfinder, wps)
    ga = GeneticAlgorithm(calculator, GeneticAlgorithmConfig(population_size=20, max_generations=5))

    p1 = list(range(8))
    p2 = list(reversed(range(8)))

    # Test OX crossover
    for _ in range(50):
        c1, c2 = ga.order_crossover(p1, p2)
        assert sorted(c1) == list(range(8)), f"Crossover corrupted chromosome: {c1}"
        assert sorted(c2) == list(range(8)), f"Crossover corrupted chromosome: {c2}"

    # Test mutation
    for _ in range(50):
        mutated = ga.mutate(p1)
        assert sorted(mutated) == list(range(8)), f"Mutation corrupted chromosome: {mutated}"


def test_same_seed_reproducibility():
    """Running GA with the same random seed must produce identical results."""
    cfg1 = PlannerConfig.from_json_file("configs/default_environment.json")
    cfg1.genetic_algorithm.random_seed = 12345
    cfg1.export_plots = False

    cfg2 = PlannerConfig.from_json_file("configs/default_environment.json")
    cfg2.genetic_algorithm.random_seed = 12345
    cfg2.export_plots = False

    service1 = GlobalPlannerService(cfg1)
    env1 = service1.generate_environment(cfg1.environment)
    route1 = service1.plan_route(env1, cfg1)

    service2 = GlobalPlannerService(cfg2)
    env2 = service2.generate_environment(cfg2.environment)
    route2 = service2.plan_route(env2, cfg2)

    assert route1.status == "success"
    assert route2.status == "success"
    assert route1.metrics.path_length == route2.metrics.path_length
    assert [w["id"] for w in route1.ordered_monitoring_waypoints] == [w["id"] for w in route2.ordered_monitoring_waypoints]


def test_end_to_end_planning_and_json_contract(tmp_path):
    """Verify full planning flow, metrics generation, and AirSim JSON schema contract."""
    cfg = PlannerConfig.from_json_file("configs/default_environment.json")
    cfg.output_directory = str(tmp_path)
    cfg.export_plots = False

    service = GlobalPlannerService(cfg)
    env = service.generate_environment(cfg.environment)
    route: PlannedRoute = service.plan_route(env, cfg)

    assert route.status == "success"
    assert route.validation.is_valid is True
    assert route.metrics.visited_waypoints == 6
    assert route.metrics.required_waypoints == 6
    assert route.metrics.coverage_percentage == 100.0
    assert route.metrics.collision_count == 0
    assert route.metrics.minimum_obstacle_clearance >= cfg.environment.safety_clearance

    # Export to JSON
    json_path = tmp_path / "route_contract.json"
    exported = service.export_route(route, json_path)
    assert exported.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Verify AirSim Integration Contract Schema
    assert data["schema_version"] == "1.0"
    assert data["planner"] == "GA_2OPT_ASTAR"
    assert data["status"] == "success"
    assert data["coordinate_frame"] == "planner_xy_altitude_up"
    assert "start" in data and "x" in data["start"] and "altitude" in data["start"]
    assert "destination" in data and "x" in data["destination"] and "altitude" in data["destination"]
    assert len(data["ordered_monitoring_waypoints"]) == 6
    assert len(data["path_points"]) > 10
    assert data["metrics"]["collision_count"] == 0
    assert data["metrics"]["coverage_percentage"] == 100.0
    assert data["validation"]["is_valid"] is True
    assert data["validation"]["errors"] == []


def test_failure_reported_on_impossible_environment():
    """If waypoints or targets are unreachable, planner must explicitly report failure."""
    cfg = PlannerConfig.from_json_file("configs/default_environment.json")
    cfg.export_plots = False

    # Block destination inside an impenetrable obstacle box
    service = GlobalPlannerService(cfg)
    env = service.generate_environment(cfg.environment)
    # Box around destination (95, 95)
    env.obstacle_manager.add_rectangular_obstacle("impenetrable_wall", 90.0, 99.0, 90.0, 99.0)

    route = service.plan_route(env, cfg)
    assert route.status == "failure"
    assert route.validation.is_valid is False
    assert len(route.validation.errors) > 0


def test_continuous_route_geometry_no_large_jumps():
    """Regression test: exported route must have continuous grid steps (no 35m/54m jumps) and exact length."""
    import math

    cfg = PlannerConfig.from_json_file("configs/default_environment.json")
    cfg.export_plots = False
    service = GlobalPlannerService(cfg)
    env = service.generate_environment(cfg.environment)
    route = service.plan_route(env, cfg)

    assert route.status == "success"
    pts = route.path_points
    assert len(pts) > 200  # Dense 1m grid steps rather than stripped collinear endpoints

    max_allowed_step = cfg.environment.grid_resolution * 1.6
    computed_len = 0.0
    for i in range(len(pts) - 1):
        step_dist = math.hypot(pts[i + 1]["x"] - pts[i]["x"], pts[i + 1]["y"] - pts[i]["y"])
        assert step_dist <= max_allowed_step, (
            f"Discontinuous step {step_dist:.2f}m between index {i} ({pts[i]}) and {i+1} ({pts[i+1]})"
        )
        computed_len += step_dist

    assert abs(computed_len - route.metrics.path_length) < 0.05


def test_failed_astar_segment_does_not_fallback_to_straight_line():
    """Verify that if an A* segment fails during reconstruction, no straight-line fallback is inserted."""
    cfg = PlannerConfig.from_json_file("configs/default_environment.json")
    cfg.export_plots = False
    service = GlobalPlannerService(cfg)
    env = service.generate_environment(cfg.environment)
    # Enclose waypoint salt_lick_echo (55, 85) inside a box wall so A* segment to it fails
    env.obstacle_manager.add_rectangular_obstacle("box_around_echo", 50.0, 60.0, 80.0, 90.0)

    route = service.plan_route(env, cfg)
    assert route.status == "failure"
    assert route.validation.is_valid is False
    assert any("is infeasible" in err for err in route.validation.errors)
