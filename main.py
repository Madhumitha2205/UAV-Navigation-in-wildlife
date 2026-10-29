#!/usr/bin/env python3
"""Main entry point for UAV Global Route Planning Backend.

Executes Genetic Algorithm with 2-Opt and Obstacle-Aware A* pathfinding.
Exports route to AirSim integration JSON and generates visualization plots.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path so backend package is importable
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.global_planner.config import PlannerConfig
from backend.global_planner.planner_service import GlobalPlannerService, PlannedRoute


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="UAV Global Route Planning Backend (GA + 2-Opt + A*)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="configs/default_environment.json",
        help="Path to JSON environment configuration file",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="outputs",
        help="Directory to save generated JSON route and plots",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Disable Matplotlib visualization plot generation",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    if not config_path.exists():
        print(f"[ERROR] Configuration file not found: {config_path}", file=sys.stderr)
        return 1

    print("=" * 70)
    print("   UAV GLOBAL ROUTE PLANNING BACKEND: GA + 2-OPT + A*")
    print("   Hierarchical Navigation Framework for Wildlife Monitoring")
    print("=" * 70)
    print(f"Loading configuration from: {config_path}")

    try:
        config = PlannerConfig.from_json_file(config_path)
    except Exception as e:
        print(f"[FATAL] Failed to parse configuration: {e}", file=sys.stderr)
        return 1

    # Override options from CLI arguments
    if args.output_dir:
        config.output_directory = args.output_dir
    if args.no_plots:
        config.export_plots = False

    output_dir = Path(config.output_directory)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    config.output_directory = str(output_dir)

    print("\n--- Mission Environment Parameters ---")
    print(f"Map Bounds: [{config.environment.x_min}, {config.environment.x_max}] x [{config.environment.y_min}, {config.environment.y_max}]")
    print(f"Start Position: ({config.environment.start.x}, {config.environment.start.y}) alt={config.environment.start.altitude}m")
    print(f"Destination:    ({config.environment.destination.x}, {config.environment.destination.y}) alt={config.environment.destination.altitude}m")
    print(f"Safety Clearance: {config.environment.safety_clearance} meters")
    print(f"Grid Resolution:  {config.environment.grid_resolution} meters")
    print(f"Obstacles: {len(config.environment.circular_obstacles)} circular, {len(config.environment.rectangular_obstacles)} rectangular, {len(config.environment.dynamic_obstacles)} dynamic snapshots")
    print(f"Configured Waypoints: {len(config.environment.monitoring_waypoints)}")

    print("\n--- Optimization Hyperparameters ---")
    print(f"Population Size: {config.genetic_algorithm.population_size}")
    print(f"Max Generations: {config.genetic_algorithm.max_generations}")
    print(f"Crossover Rate:  {config.genetic_algorithm.crossover_probability} (Order Crossover)")
    print(f"Mutation Rate:   {config.genetic_algorithm.mutation_probability} (Swap/Inversion)")
    print(f"2-Opt Refinement: Every {config.genetic_algorithm.two_opt_frequency} gens on top {int(config.genetic_algorithm.two_opt_candidate_ratio*100)}%")
    print(f"Random Seed:     {config.genetic_algorithm.random_seed}")

    service = GlobalPlannerService(config)

    print("\n[INFO] Initializing environment and obstacle-aware A* path precomputation...")
    env = service.generate_environment(config.environment)

    print("[INFO] Executing GA evolution with 2-Opt local search...")
    route: PlannedRoute = service.plan_route(env, config)

    # Export route JSON
    json_path = output_dir / "planned_route.json"
    service.export_route(route, json_path)
    print(f"[SUCCESS] Exported route contract to: {json_path}")

    # Print Results
    print("\n" + "=" * 70)
    print("                     PLANNING RESULTS SUMMARY")
    print("=" * 70)
    print(f"Status:                      {route.status.upper()}")
    print(f"Independent Validation:      {'PASSED' if route.validation.is_valid else 'FAILED'}")
    print(f"Total Path Length:           {route.metrics.path_length:.2f} meters")
    print(f"Waypoint Coverage:           {route.metrics.coverage_percentage:.1f}% ({route.metrics.visited_waypoints}/{route.metrics.required_waypoints})")
    print(f"Obstacle Collision Count:    {route.metrics.collision_count}")
    min_clear = route.metrics.minimum_obstacle_clearance
    print(f"Minimum Obstacle Clearance:  {min_clear:.2f} m" if min_clear is not None else "Minimum Obstacle Clearance:  N/A")
    print(f"Planning Runtime:            {route.metrics.planning_time_seconds:.3f} seconds")
    print(f"Generations Completed:       {route.metrics.generations_completed}")
    print(f"2-Opt Improvements:          {route.metrics.two_opt_improvements}")
    print(f"Total Waypoint Path Points:  {len(route.path_points)}")

    if route.ordered_monitoring_waypoints:
        print("\nOptimal Waypoint Visit Order:")
        for wp in route.ordered_monitoring_waypoints:
            print(f"  Step {wp['order']:2d}: {wp['id']:25s} at ({wp['x']:6.2f}, {wp['y']:6.2f})")

    if route.validation.errors:
        print("\n[VALIDATION ERRORS]:")
        for err in route.validation.errors:
            print(f"  - {err}")

    if route.validation.warnings:
        print("\n[VALIDATION WARNINGS]:")
        for warn in route.validation.warnings:
            print(f"  - {warn}")

    if config.export_plots and route.status == "success":
        print(f"\nGenerated Plots:")
        print(f"  - Route Trajectory: {output_dir / 'optimized_route.png'}")
        print(f"  - Fitness History:  {output_dir / 'fitness_history.png'}")

    print("=" * 70)

    return 0 if route.status == "success" else 2


if __name__ == "__main__":
    sys.exit(main())
