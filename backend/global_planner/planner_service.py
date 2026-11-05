"""Planner service orchestrating environment generation, pathfinding, GA, 2-Opt, and JSON export.

Provides the primary public API and AirSim integration contract for the UAV global route planning framework.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.global_planner.config import PlannerConfig, EnvironmentConfig
from backend.global_planner.environment import Environment, Waypoint
from backend.global_planner.grid_pathfinder import GridPathfinder, PathResult
from backend.global_planner.fitness import RouteFitnessCalculator
from backend.global_planner.genetic_algorithm import GeneticAlgorithm, GAResult
from backend.global_planner.two_opt import TwoOptOptimizer
from backend.global_planner.route_validator import RouteValidator, ValidationReport
from backend.global_planner.visualization import Visualizer
from backend.global_planner.waypoint_generator import WaypointGenerator


@dataclass
class RouteMetrics:
    """Quantitative performance metrics for the planned UAV trajectory."""

    path_length: float = 0.0
    coverage_percentage: float = 0.0
    visited_waypoints: int = 0
    required_waypoints: int = 0
    collision_count: int = 0
    minimum_obstacle_clearance: Optional[float] = None
    planning_time_seconds: float = 0.0
    generations_completed: int = 0
    two_opt_improvements: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_length": round(self.path_length, 4),
            "coverage_percentage": round(self.coverage_percentage, 2),
            "visited_waypoints": self.visited_waypoints,
            "required_waypoints": self.required_waypoints,
            "collision_count": self.collision_count,
            "minimum_obstacle_clearance": (
                round(self.minimum_obstacle_clearance, 4)
                if self.minimum_obstacle_clearance is not None
                else None
            ),
            "planning_time_seconds": round(self.planning_time_seconds, 4),
            "generations_completed": self.generations_completed,
            "two_opt_improvements": self.two_opt_improvements,
        }


@dataclass
class PlannedRoute:
    """Complete flight plan produced by the global route planner."""

    status: str  # "success" or "failure"
    planner: str
    coordinate_frame: str
    start: Dict[str, float]
    destination: Dict[str, float]
    ordered_monitoring_waypoints: List[Dict[str, Any]]
    path_points: List[Dict[str, Any]]
    metrics: RouteMetrics
    validation: ValidationReport
    fitness_history: List[float] = field(default_factory=list)
    cost_history: List[float] = field(default_factory=list)
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "planner": self.planner,
            "status": self.status,
            "coordinate_frame": self.coordinate_frame,
            "start": self.start,
            "destination": self.destination,
            "ordered_monitoring_waypoints": self.ordered_monitoring_waypoints,
            "path_points": self.path_points,
            "metrics": self.metrics.to_dict(),
            "validation": self.validation.to_dict(),
        }


class GlobalPlannerService:
    """Service facade managing end-to-end UAV global route planning."""

    def __init__(self, config: Optional[PlannerConfig] = None):
        self.config = config if config is not None else PlannerConfig()

    def generate_environment(self, config: Optional[EnvironmentConfig] = None) -> Environment:
        """Create and validate an Environment from configuration."""
        env_conf = config if config is not None else self.config.environment
        env = Environment.from_config(env_conf)
        errors = env.validate()
        if errors:
            raise ValueError("Environment configuration errors:\n" + "\n".join(f"- {e}" for e in errors))
        return env

    def generate_monitoring_waypoints(
        self,
        environment: Environment,
        config: Optional[PlannerConfig] = None,
    ) -> List[Waypoint]:
        """Generate surveillance waypoints using Snake-Grid pattern or return configured waypoints."""
        cfg = config if config is not None else self.config
        wp_gen_cfg = cfg.environment.waypoint_generation

        if wp_gen_cfg.enabled and wp_gen_cfg.pattern == "snake_grid":
            gen = WaypointGenerator(environment)
            waypoints = gen.generate_snake_grid(
                region_bounds=wp_gen_cfg.bounds,
                step_x=wp_gen_cfg.step_x,
                step_y=wp_gen_cfg.step_y,
                altitude=wp_gen_cfg.default_altitude,
                importance_weight=wp_gen_cfg.default_importance,
            )
            environment.set_monitoring_waypoints(waypoints)
            return waypoints

        # Otherwise use existing configured waypoints
        return environment.monitoring_waypoints

    def plan_route(
        self,
        environment: Environment,
        config: Optional[PlannerConfig] = None,
        preserve_waypoint_order: bool = False,
    ) -> PlannedRoute:
        """Execute full hierarchical planning: A* grid pathfinder -> GA -> 2-Opt -> Validation."""
        cfg = config if config is not None else self.config
        start_time = time.time()

        # Step 1: Ensure waypoints exist
        monitoring_wps = list(environment.monitoring_waypoints)
        if not monitoring_wps:
            monitoring_wps = self.generate_monitoring_waypoints(environment, cfg)

        # Step 2: Initialize Obstacle-Aware A* Pathfinder
        pathfinder = GridPathfinder(environment)

        # Step 3: Build Pairwise Distance Matrix and Fitness Evaluator
        fitness_calc = RouteFitnessCalculator(
            environment=environment,
            pathfinder=pathfinder,
            waypoints=monitoring_wps,
        )

        # Step 4: Initialize 2-Opt Optimizer
        two_opt = TwoOptOptimizer(fitness_calculator=fitness_calc, config=cfg.two_opt)

        # Step 5: Execute Genetic Algorithm (or preserve explicit user order)
        if preserve_waypoint_order and len(monitoring_wps) > 0:
            user_seq = list(range(len(monitoring_wps)))
            cost, is_feasible, _ = fitness_calc.evaluate_chromosome(user_seq)
            fitness = fitness_calc.cost_to_fitness(cost)
            ga_result = GAResult(
                success=is_feasible,
                best_chromosome=user_seq,
                best_cost=cost,
                is_feasible=is_feasible,
                fitness_history=[fitness],
                best_cost_history=[cost],
                generations_completed=1,
                two_opt_improvements=0,
            )
        else:
            ga = GeneticAlgorithm(
                fitness_calculator=fitness_calc,
                config=cfg.genetic_algorithm,
                two_opt_optimizer=two_opt,
            )
            ga_result = ga.run()

        # Step 6: Reconstruct Full Continuous Path Geometry
        ordered_waypoints: List[Waypoint] = []
        path_points_2d: List[Tuple[float, float]] = []
        segment_errors: List[str] = []

        if ga_result.best_chromosome is not None:
            for idx in ga_result.best_chromosome:
                ordered_waypoints.append(fitness_calc.waypoints[idx])

            # Build full path: start -> wp[0] -> wp[1] -> ... -> destination
            node_sequence = (
                [fitness_calc.start_idx]
                + [k + 1 for k in ga_result.best_chromosome]
                + [fitness_calc.dest_idx]
            )

            for i in range(len(node_sequence) - 1):
                n_from = node_sequence[i]
                n_to = node_sequence[i + 1]
                expected_from = fitness_calc.node_positions[n_from]
                expected_to = fitness_calc.node_positions[n_to]
                seg_result = fitness_calc.get_segment_path(n_from, n_to)

                if not seg_result.success or len(seg_result.path_points) < 2:
                    segment_errors.append(
                        f"Segment {i} (node {n_from} {expected_from} -> node {n_to} {expected_to}) is infeasible: "
                        f"{seg_result.error_message or 'empty path'}"
                    )
                    break

                actual_seg_start = seg_result.path_points[0]
                actual_seg_end = seg_result.path_points[-1]
                if math.hypot(actual_seg_start[0] - expected_from[0], actual_seg_start[1] - expected_from[1]) > 1e-3:
                    segment_errors.append(
                        f"Segment {i} start mismatch: expected {expected_from}, got {actual_seg_start}."
                    )
                    break
                if math.hypot(actual_seg_end[0] - expected_to[0], actual_seg_end[1] - expected_to[1]) > 1e-3:
                    segment_errors.append(
                        f"Segment {i} end mismatch: expected {expected_to}, got {actual_seg_end}."
                    )
                    break

                if not path_points_2d:
                    path_points_2d.extend(seg_result.path_points)
                else:
                    prev_junction = path_points_2d[-1]
                    if math.hypot(prev_junction[0] - actual_seg_start[0], prev_junction[1] - actual_seg_start[1]) > 1e-3:
                        segment_errors.append(
                            f"Discontinuous segment join at segment {i}: previous end {prev_junction} != segment start {actual_seg_start}."
                        )
                        break
                    path_points_2d.extend(seg_result.path_points[1:])

        # Step 7: Independent Route Validation
        max_step_allowed = environment.grid_resolution * math.sqrt(2.0) * 1.5
        validator = RouteValidator(environment)
        validation_report = validator.validate_route(
            ordered_waypoints=ordered_waypoints,
            path_points=path_points_2d,
            reported_path_length=ga_result.best_cost if (ga_result.success and not segment_errors) else None,
            required_waypoints=monitoring_wps,
            max_segment_step=max_step_allowed,
        )
        if segment_errors:
            validation_report.errors = segment_errors + validation_report.errors
            validation_report.is_valid = False

        elapsed_time = time.time() - start_time

        # Step 8: Calculate Final Metrics
        status = "success" if (ga_result.success and validation_report.is_valid) else "failure"

        # If validation failed, ensure status is marked failure
        if not validation_report.is_valid and ga_result.success:
            status = "failure"
            if not ga_result.error_message:
                ga_result.error_message = "Route failed independent post-planning validation."

        metrics = RouteMetrics(
            path_length=validation_report.details.get("calculated_path_length", 0.0),
            coverage_percentage=validation_report.details.get("coverage_percentage", 0.0),
            visited_waypoints=len(ordered_waypoints),
            required_waypoints=len(monitoring_wps),
            collision_count=validation_report.details.get("collision_count", 0),
            minimum_obstacle_clearance=validation_report.details.get(
                "minimum_obstacle_clearance"
            ),
            planning_time_seconds=elapsed_time,
            generations_completed=ga_result.generations_completed,
            two_opt_improvements=ga_result.two_opt_improvements,
        )

        # Build AirSim contract formatted points with altitude and monitoring metadata
        default_alt = environment.default_altitude
        formatted_wps: List[Dict[str, Any]] = []
        for idx, wp in enumerate(ordered_waypoints):
            formatted_wps.append(
                {
                    "order": idx + 1,
                    "id": wp.id,
                    "x": round(wp.x, 4),
                    "y": round(wp.y, 4),
                    "altitude": round(wp.altitude, 2),
                    "importance_weight": round(wp.importance_weight, 4),
                    "is_mandatory": bool(wp.is_mandatory),
                }
            )

        # Match ordered monitoring waypoints to their sequential positions along path_points_2d
        wp_point_map: Dict[int, Waypoint] = {}
        search_idx = 0
        for wp in ordered_waypoints:
            for p_idx in range(search_idx, len(path_points_2d)):
                if math.hypot(path_points_2d[p_idx][0] - wp.x, path_points_2d[p_idx][1] - wp.y) <= 1e-2:
                    wp_point_map[p_idx] = wp
                    search_idx = p_idx
                    break

        formatted_path_points: List[Dict[str, Any]] = []
        for idx, pt in enumerate(path_points_2d):
            matched_wp = wp_point_map.get(idx)
            if matched_wp is not None:
                alt = matched_wp.altitude
                is_mon = True
                wp_id: Optional[str] = matched_wp.id
            elif idx == 0:
                alt = environment.start.altitude
                is_mon = False
                wp_id = "START"
            elif idx == len(path_points_2d) - 1:
                alt = environment.destination.altitude
                is_mon = False
                wp_id = "DEST"
            else:
                alt = default_alt
                is_mon = False
                wp_id = None

            formatted_path_points.append(
                {
                    "point_index": idx,
                    "x": round(pt[0], 4),
                    "y": round(pt[1], 4),
                    "altitude": round(alt, 2),
                    "is_monitoring": is_mon,
                    "waypoint_id": wp_id,
                }
            )

        start_dict = {
            "x": round(environment.start.x, 4),
            "y": round(environment.start.y, 4),
            "altitude": round(environment.start.altitude, 2),
        }
        dest_dict = {
            "x": round(environment.destination.x, 4),
            "y": round(environment.destination.y, 4),
            "altitude": round(environment.destination.altitude, 2),
        }

        planned_route = PlannedRoute(
            status=status,
            planner="GA_2OPT_ASTAR",
            coordinate_frame="planner_xy_altitude_up",
            start=start_dict,
            destination=dest_dict,
            ordered_monitoring_waypoints=formatted_wps,
            path_points=formatted_path_points,
            metrics=metrics,
            validation=validation_report,
            fitness_history=ga_result.fitness_history,
            cost_history=ga_result.best_cost_history,
        )

        # Step 9: Visualization Export if configured
        if cfg.export_plots and status == "success":
            out_dir = Path(cfg.output_directory)
            out_dir.mkdir(parents=True, exist_ok=True)
            vis = Visualizer(environment)
            vis.plot_route(
                path_points=path_points_2d,
                ordered_waypoints=ordered_waypoints,
                output_path=out_dir / "optimized_route.png",
            )
            vis.plot_fitness_history(
                cost_history=ga_result.best_cost_history,
                fitness_history=ga_result.fitness_history,
                output_path=out_dir / "fitness_history.png",
            )

        return planned_route

    def validate_route(
        self,
        route: PlannedRoute,
        environment: Environment,
    ) -> ValidationReport:
        """Validate an existing PlannedRoute against an Environment."""
        validator = RouteValidator(environment)
        pts = [(p["x"], p["y"]) for p in route.path_points]
        wps = [
            Waypoint(
                id=w["id"],
                x=w["x"],
                y=w["y"],
                altitude=w["altitude"],
                importance_weight=w.get("importance_weight", 1.0),
            )
            for w in route.ordered_monitoring_waypoints
        ]
        return validator.validate_route(
            ordered_waypoints=wps,
            path_points=pts,
            reported_path_length=route.metrics.path_length,
            required_waypoints=environment.monitoring_waypoints,
            max_segment_step=environment.grid_resolution * math.sqrt(2.0) * 1.5,
        )

    def export_route(
        self,
        route: PlannedRoute,
        output_path: str | Path,
    ) -> Path:
        """Export route to a documented AirSim integration JSON contract."""
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(route.to_dict(), f, indent=2)
        return out_file

    def export_controller_route(
        self,
        route: PlannedRoute,
        output_path: str | Path,
        environment: Optional[Environment] = None,
        mission_id: str = "wildlife_monitoring_generated_route",
    ) -> Path:
        """Convert and export a validated PlannedRoute into the Part 2 Controller Route JSON schema.

        Authoritative planner output: `planned_route.json`
        Controller input contract: `controller_route.json`
        """
        from backend.intelligent_control.route_loader import convert_planned_route_dict_to_controller_dict, load_global_route

        env_obs: List[Dict[str, Any]] = []
        if environment is not None:
            from backend.global_planner.obstacle_manager import CircularObstacle, RectangularObstacle

            default_z = float(environment.default_altitude)
            for obs in environment.obstacle_manager.obstacles:
                if isinstance(obs, CircularObstacle):
                    env_obs.append(
                        {
                            "id": obs.id,
                            "x": round(obs.x, 4),
                            "y": round(obs.y, 4),
                            "z": round(default_z, 2),
                            "radius": round(obs.radius, 4),
                        }
                    )
                elif isinstance(obs, RectangularObstacle):
                    cx = 0.5 * (obs.x_min + obs.x_max)
                    cy = 0.5 * (obs.y_min + obs.y_max)
                    r = 0.5 * math.hypot(obs.x_max - obs.x_min, obs.y_max - obs.y_min)
                    env_obs.append(
                        {
                            "id": obs.id,
                            "x": round(cx, 4),
                            "y": round(cy, 4),
                            "z": round(default_z, 2),
                            "radius": round(r, 4),
                        }
                    )

        ctrl_dict = convert_planned_route_dict_to_controller_dict(
            route.to_dict(),
            mission_id=mission_id,
            static_obstacles=env_obs,
        )
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(ctrl_dict, f, indent=2)

        # Immediately verify the exported file passes strict controller schema validation
        load_global_route(out_file)
        return out_file
