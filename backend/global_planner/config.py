"""Configuration management for the UAV Global Route Planning Backend.

Provides typed, validated configuration models for the environment,
pathfinding, genetic algorithm, 2-Opt optimization, and waypoint generation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Point3DConfig:
    x: float
    y: float
    altitude: float = 10.0

    def to_tuple_2d(self) -> Tuple[float, float]:
        return (float(self.x), float(self.y))

    def to_tuple_3d(self) -> Tuple[float, float, float]:
        return (float(self.x), float(self.y), float(self.altitude))


@dataclass
class CircularObstacleConfig:
    id: str
    x: float
    y: float
    radius: float


@dataclass
class RectangularObstacleConfig:
    id: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float


@dataclass
class MonitoringWaypointConfig:
    id: str
    x: float
    y: float
    altitude: float = 10.0
    importance_weight: float = 1.0
    is_mandatory: bool = True


@dataclass
class WaypointGeneratorConfig:
    enabled: bool = False
    pattern: str = "snake_grid"  # 'snake_grid' or 'user_defined'
    bounds: Optional[Tuple[float, float, float, float]] = None  # (x_min, x_max, y_min, y_max)
    step_x: float = 20.0
    step_y: float = 20.0
    default_altitude: float = 10.0
    default_importance: float = 1.0


@dataclass
class EnvironmentConfig:
    x_min: float = 0.0
    x_max: float = 100.0
    y_min: float = 0.0
    y_max: float = 100.0
    default_altitude: float = 10.0
    safety_clearance: float = 2.0
    grid_resolution: float = 1.0
    start: Point3DConfig = field(default_factory=lambda: Point3DConfig(x=5.0, y=5.0, altitude=10.0))
    destination: Point3DConfig = field(
        default_factory=lambda: Point3DConfig(x=95.0, y=95.0, altitude=10.0)
    )
    circular_obstacles: List[CircularObstacleConfig] = field(default_factory=list)
    rectangular_obstacles: List[RectangularObstacleConfig] = field(default_factory=list)
    dynamic_obstacles: List[CircularObstacleConfig] = field(default_factory=list)
    monitoring_waypoints: List[MonitoringWaypointConfig] = field(default_factory=list)
    waypoint_generation: WaypointGeneratorConfig = field(
        default_factory=WaypointGeneratorConfig
    )

    def validate(self) -> List[str]:
        """Validate environment configuration values."""
        errors: List[str] = []
        if self.x_max <= self.x_min:
            errors.append(f"x_max ({self.x_max}) must be greater than x_min ({self.x_min}).")
        if self.y_max <= self.y_min:
            errors.append(f"y_max ({self.y_max}) must be greater than y_min ({self.y_min}).")
        if self.grid_resolution <= 0.0:
            errors.append(f"grid_resolution ({self.grid_resolution}) must be positive.")
        if self.safety_clearance < 0.0:
            errors.append(f"safety_clearance ({self.safety_clearance}) must be non-negative.")

        # Validate start and destination within bounds
        if not (self.x_min <= self.start.x <= self.x_max and self.y_min <= self.start.y <= self.y_max):
            errors.append(f"Start point ({self.start.x}, {self.start.y}) is outside map bounds.")
        if not (self.x_min <= self.destination.x <= self.x_max and self.y_min <= self.destination.y <= self.y_max):
            errors.append(f"Destination point ({self.destination.x}, {self.destination.y}) is outside map bounds.")

        # Check circular obstacles
        for obs in self.circular_obstacles + self.dynamic_obstacles:
            if obs.radius <= 0.0:
                errors.append(f"Circular obstacle {obs.id} radius must be positive.")

        # Check rectangular obstacles
        for obs in self.rectangular_obstacles:
            if obs.x_max <= obs.x_min:
                errors.append(f"Rectangular obstacle {obs.id} x_max must be greater than x_min.")
            if obs.y_max <= obs.y_min:
                errors.append(f"Rectangular obstacle {obs.id} y_max must be greater than y_min.")

        return errors


@dataclass
class GeneticAlgorithmConfig:
    population_size: int = 80
    max_generations: int = 200
    crossover_probability: float = 0.8
    mutation_probability: float = 0.02
    snake_grid_init_ratio: float = 0.50
    two_opt_frequency: int = 10
    two_opt_candidate_ratio: float = 0.20
    random_seed: Optional[int] = 42
    patience: int = 50
    elite_count: int = 2

    def validate(self) -> List[str]:
        errors: List[str] = []
        if self.population_size < 4:
            errors.append(f"population_size ({self.population_size}) must be at least 4.")
        if self.max_generations < 1:
            errors.append(f"max_generations ({self.max_generations}) must be at least 1.")
        if not (0.0 <= self.crossover_probability <= 1.0):
            errors.append(f"crossover_probability ({self.crossover_probability}) must be in [0.0, 1.0].")
        if not (0.0 <= self.mutation_probability <= 1.0):
            errors.append(f"mutation_probability ({self.mutation_probability}) must be in [0.0, 1.0].")
        if not (0.0 <= self.snake_grid_init_ratio <= 1.0):
            errors.append(f"snake_grid_init_ratio ({self.snake_grid_init_ratio}) must be in [0.0, 1.0].")
        if self.two_opt_frequency < 1:
            errors.append(f"two_opt_frequency ({self.two_opt_frequency}) must be >= 1.")
        if not (0.0 <= self.two_opt_candidate_ratio <= 1.0):
            errors.append(f"two_opt_candidate_ratio ({self.two_opt_candidate_ratio}) must be in [0.0, 1.0].")
        if self.elite_count < 1 or self.elite_count >= self.population_size:
            errors.append(f"elite_count ({self.elite_count}) must be in [1, population_size).")
        return errors


@dataclass
class TwoOptConfig:
    max_iterations: int = 100
    improvement_threshold: float = 1e-4


@dataclass
class PlannerConfig:
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    genetic_algorithm: GeneticAlgorithmConfig = field(
        default_factory=GeneticAlgorithmConfig
    )
    two_opt: TwoOptConfig = field(default_factory=TwoOptConfig)
    export_plots: bool = True
    output_directory: str = "outputs"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PlannerConfig:
        env_raw = data.get("environment", {})
        start_raw = env_raw.get("start", {"x": 5.0, "y": 5.0, "altitude": 10.0})
        dest_raw = env_raw.get("destination", {"x": 95.0, "y": 95.0, "altitude": 10.0})

        start = Point3DConfig(
            x=float(start_raw.get("x", 5.0)),
            y=float(start_raw.get("y", 5.0)),
            altitude=float(start_raw.get("altitude", 10.0)),
        )
        dest = Point3DConfig(
            x=float(dest_raw.get("x", 95.0)),
            y=float(dest_raw.get("y", 95.0)),
            altitude=float(dest_raw.get("altitude", 10.0)),
        )

        circular = [
            CircularObstacleConfig(
                id=c.get("id", f"circle_{idx}"),
                x=float(c["x"]),
                y=float(c["y"]),
                radius=float(c["radius"]),
            )
            for idx, c in enumerate(env_raw.get("circular_obstacles", []))
        ]

        rectangular = [
            RectangularObstacleConfig(
                id=r.get("id", f"rect_{idx}"),
                x_min=float(r["x_min"]),
                x_max=float(r["x_max"]),
                y_min=float(r["y_min"]),
                y_max=float(r["y_max"]),
            )
            for idx, r in enumerate(env_raw.get("rectangular_obstacles", []))
        ]

        dynamic_obs = [
            CircularObstacleConfig(
                id=d.get("id", f"dynamic_{idx}"),
                x=float(d["x"]),
                y=float(d["y"]),
                radius=float(d["radius"]),
            )
            for idx, d in enumerate(env_raw.get("dynamic_obstacles", []))
        ]

        waypoints = [
            MonitoringWaypointConfig(
                id=w.get("id", f"wp_{idx:02d}"),
                x=float(w["x"]),
                y=float(w["y"]),
                altitude=float(w.get("altitude", 10.0)),
                importance_weight=float(w.get("importance_weight", 1.0)),
                is_mandatory=bool(w.get("is_mandatory", True)),
            )
            for idx, w in enumerate(env_raw.get("monitoring_waypoints", []))
        ]

        wp_gen_raw = env_raw.get("waypoint_generation", {})
        bounds_raw = wp_gen_raw.get("bounds")
        bounds_tuple = tuple(bounds_raw) if bounds_raw and len(bounds_raw) == 4 else None

        wp_gen = WaypointGeneratorConfig(
            enabled=bool(wp_gen_raw.get("enabled", False)),
            pattern=str(wp_gen_raw.get("pattern", "snake_grid")),
            bounds=bounds_tuple,
            step_x=float(wp_gen_raw.get("step_x", 20.0)),
            step_y=float(wp_gen_raw.get("step_y", 20.0)),
            default_altitude=float(wp_gen_raw.get("default_altitude", 10.0)),
            default_importance=float(wp_gen_raw.get("default_importance", 1.0)),
        )

        environment_config = EnvironmentConfig(
            x_min=float(env_raw.get("x_min", 0.0)),
            x_max=float(env_raw.get("x_max", 100.0)),
            y_min=float(env_raw.get("y_min", 0.0)),
            y_max=float(env_raw.get("y_max", 100.0)),
            default_altitude=float(env_raw.get("default_altitude", 10.0)),
            safety_clearance=float(env_raw.get("safety_clearance", 2.0)),
            grid_resolution=float(env_raw.get("grid_resolution", 1.0)),
            start=start,
            destination=dest,
            circular_obstacles=circular,
            rectangular_obstacles=rectangular,
            dynamic_obstacles=dynamic_obs,
            monitoring_waypoints=waypoints,
            waypoint_generation=wp_gen,
        )

        ga_raw = data.get("genetic_algorithm", {})
        ga_config = GeneticAlgorithmConfig(
            population_size=int(ga_raw.get("population_size", 80)),
            max_generations=int(ga_raw.get("max_generations", 200)),
            crossover_probability=float(ga_raw.get("crossover_probability", 0.8)),
            mutation_probability=float(ga_raw.get("mutation_probability", 0.02)),
            snake_grid_init_ratio=float(ga_raw.get("snake_grid_init_ratio", 0.50)),
            two_opt_frequency=int(ga_raw.get("two_opt_frequency", 10)),
            two_opt_candidate_ratio=float(ga_raw.get("two_opt_candidate_ratio", 0.20)),
            random_seed=ga_raw.get("random_seed", 42),
            patience=int(ga_raw.get("patience", 50)),
            elite_count=int(ga_raw.get("elite_count", 2)),
        )

        two_opt_raw = data.get("two_opt", {})
        two_opt_config = TwoOptConfig(
            max_iterations=int(two_opt_raw.get("max_iterations", 100)),
            improvement_threshold=float(two_opt_raw.get("improvement_threshold", 1e-4)),
        )

        return cls(
            environment=environment_config,
            genetic_algorithm=ga_config,
            two_opt=two_opt_config,
            export_plots=bool(data.get("export_plots", True)),
            output_directory=str(data.get("output_directory", "outputs")),
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> PlannerConfig:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        config = cls.from_dict(data)
        errors = config.validate()
        if errors:
            raise ValueError(f"Configuration validation errors in {path}:\n" + "\n".join(f"- {e}" for e in errors))
        return config

    def validate(self) -> List[str]:
        errors = self.environment.validate()
        errors.extend(self.genetic_algorithm.validate())
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
