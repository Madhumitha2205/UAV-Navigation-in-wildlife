"""Environment model and coordinate system for UAV route planning.

Defines 2D spatial environment with altitude metadata, bounds, start,
destination, required monitoring waypoints, and obstacle constraints.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from backend.global_planner.config import EnvironmentConfig, Point3DConfig
from backend.global_planner.obstacle_manager import (
    CircularObstacle,
    ObstacleManager,
    RectangularObstacle,
)


@dataclass
class Waypoint:
    """Represents a monitoring waypoint or navigation target."""

    id: str
    x: float
    y: float
    altitude: float = 10.0
    importance_weight: float = 1.0
    is_mandatory: bool = True

    def to_tuple_2d(self) -> Tuple[float, float]:
        return (float(self.x), float(self.y))

    def to_tuple_3d(self) -> Tuple[float, float, float]:
        return (float(self.x), float(self.y), float(self.altitude))

    def distance_to(self, other: Waypoint | Tuple[float, float]) -> float:
        if isinstance(other, Waypoint):
            return math.hypot(self.x - other.x, self.y - other.y)
        return math.hypot(self.x - other[0], self.y - other[1])

    def to_dict(self) -> Dict[str, any]:
        return {
            "id": self.id,
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "altitude": round(self.altitude, 2),
            "importance_weight": round(self.importance_weight, 4),
            "is_mandatory": self.is_mandatory,
        }


class Environment:
    """Configurable 2D UAV planning environment with safety clearance and obstacles."""

    def __init__(
        self,
        x_min: float = 0.0,
        x_max: float = 100.0,
        y_min: float = 0.0,
        y_max: float = 100.0,
        start: Optional[Waypoint] = None,
        destination: Optional[Waypoint] = None,
        safety_clearance: float = 2.0,
        grid_resolution: float = 1.0,
        default_altitude: float = 10.0,
    ):
        self.x_min = float(x_min)
        self.x_max = float(x_max)
        self.y_min = float(y_min)
        self.y_max = float(y_max)
        self.safety_clearance = max(0.0, float(safety_clearance))
        self.grid_resolution = float(grid_resolution)
        self.default_altitude = float(default_altitude)

        self.start = (
            start
            if start is not None
            else Waypoint("start", 5.0, 5.0, altitude=default_altitude)
        )
        self.destination = (
            destination
            if destination is not None
            else Waypoint("destination", 95.0, 95.0, altitude=default_altitude)
        )

        self.obstacle_manager = ObstacleManager(default_clearance=self.safety_clearance)
        self.monitoring_waypoints: List[Waypoint] = []

    @classmethod
    def from_config(cls, config: EnvironmentConfig) -> Environment:
        """Create Environment instance from EnvironmentConfig."""
        start_wp = Waypoint(
            id="start",
            x=config.start.x,
            y=config.start.y,
            altitude=config.start.altitude,
        )
        dest_wp = Waypoint(
            id="destination",
            x=config.destination.x,
            y=config.destination.y,
            altitude=config.destination.altitude,
        )

        env = cls(
            x_min=config.x_min,
            x_max=config.x_max,
            y_min=config.y_min,
            y_max=config.y_max,
            start=start_wp,
            destination=dest_wp,
            safety_clearance=config.safety_clearance,
            grid_resolution=config.grid_resolution,
            default_altitude=config.default_altitude,
        )

        # Add circular obstacles
        for c in config.circular_obstacles:
            env.obstacle_manager.add_circular_obstacle(
                obstacle_id=c.id, x=c.x, y=c.y, radius=c.radius, is_dynamic=False
            )

        # Add rectangular obstacles
        for r in config.rectangular_obstacles:
            env.obstacle_manager.add_rectangular_obstacle(
                obstacle_id=r.id,
                x_min=r.x_min,
                x_max=r.x_max,
                y_min=r.y_min,
                y_max=r.y_max,
                is_dynamic=False,
            )

        # Add dynamic obstacle snapshots
        for d in config.dynamic_obstacles:
            env.obstacle_manager.add_circular_obstacle(
                obstacle_id=d.id, x=d.x, y=d.y, radius=d.radius, is_dynamic=True
            )

        # Add user-defined monitoring waypoints
        for w in config.monitoring_waypoints:
            env.add_monitoring_waypoint(
                Waypoint(
                    id=w.id,
                    x=w.x,
                    y=w.y,
                    altitude=w.altitude,
                    importance_weight=w.importance_weight,
                    is_mandatory=w.is_mandatory,
                )
            )

        return env

    def add_monitoring_waypoint(self, waypoint: Waypoint) -> None:
        """Add a monitoring waypoint to the environment."""
        self.monitoring_waypoints.append(waypoint)

    def set_monitoring_waypoints(self, waypoints: List[Waypoint]) -> None:
        """Replace all monitoring waypoints."""
        self.monitoring_waypoints = list(waypoints)

    def get_waypoint_by_id(self, wp_id: str) -> Optional[Waypoint]:
        """Lookup waypoint by identifier."""
        if self.start.id == wp_id:
            return self.start
        if self.destination.id == wp_id:
            return self.destination
        for wp in self.monitoring_waypoints:
            if wp.id == wp_id:
                return wp
        return None

    def is_inside_bounds(self, x: float, y: float) -> bool:
        """Check if coordinates fall strictly inside map boundary limits."""
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max

    def is_valid_position(
        self,
        x: float,
        y: float,
        clearance: Optional[float] = None,
    ) -> bool:
        """Return True if point is inside bounds and collision-free with clearance."""
        if not self.is_inside_bounds(x, y):
            return False
        return not self.obstacle_manager.point_collides(x, y, clearance=clearance)

    def validate(self) -> List[str]:
        """Validate entire environment setup for consistency and collision violations."""
        errors: List[str] = []

        if self.x_max <= self.x_min:
            errors.append(f"Invalid X bounds: x_min ({self.x_min}) >= x_max ({self.x_max})")
        if self.y_max <= self.y_min:
            errors.append(f"Invalid Y bounds: y_min ({self.y_min}) >= y_max ({self.y_max})")
        if self.grid_resolution <= 0:
            errors.append(f"Grid resolution must be positive: {self.grid_resolution}")
        if self.safety_clearance < 0:
            errors.append(f"Safety clearance cannot be negative: {self.safety_clearance}")

        # Check start
        if not self.is_inside_bounds(self.start.x, self.start.y):
            errors.append(f"Start ({self.start.x}, {self.start.y}) is out of bounds.")
        elif self.obstacle_manager.point_collides(self.start.x, self.start.y, self.safety_clearance):
            errors.append(
                f"Start ({self.start.x}, {self.start.y}) collides with obstacle/clearance buffer."
            )

        # Check destination
        if not self.is_inside_bounds(self.destination.x, self.destination.y):
            errors.append(f"Destination ({self.destination.x}, {self.destination.y}) is out of bounds.")
        elif self.obstacle_manager.point_collides(
            self.destination.x, self.destination.y, self.safety_clearance
        ):
            errors.append(
                f"Destination ({self.destination.x}, {self.destination.y}) collides with obstacle/clearance buffer."
            )

        # Check waypoints
        seen_ids = set()
        for wp in self.monitoring_waypoints:
            if wp.id in seen_ids:
                errors.append(f"Duplicate waypoint ID: {wp.id}")
            seen_ids.add(wp.id)

            if not self.is_inside_bounds(wp.x, wp.y):
                errors.append(f"Waypoint {wp.id} ({wp.x}, {wp.y}) is out of bounds.")
            elif self.obstacle_manager.point_collides(wp.x, wp.y, self.safety_clearance):
                errors.append(
                    f"Waypoint {wp.id} ({wp.x}, {wp.y}) collides with obstacle/clearance buffer."
                )

        return errors
