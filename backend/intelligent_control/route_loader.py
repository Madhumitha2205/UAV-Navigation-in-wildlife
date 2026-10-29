"""Route loader and schema validator for Global Planner JSON output.

The global planner (Part 1: GA + 2-Opt + A*) exports a JSON file containing:
- start_position
- destination
- monitoring_waypoints
- intermediate_path_points
- path_metrics
- validation
- coordinate_convention
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


class RouteValidationError(ValueError):
    """Raised when the global route JSON fails schema or planning validation."""


@dataclass
class RoutePoint:
    x: float
    y: float
    z: float
    is_monitoring: bool = False
    waypoint_id: Optional[str] = None
    zone_name: Optional[str] = None
    priority: int = 1

    def to_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass
class StaticObstacleSpec:
    id: str
    x: float
    y: float
    z: float
    radius: float


@dataclass
class GlobalRoute:
    mission_id: str
    planner_algorithm: str
    coordinate_convention: Dict[str, Any]
    start_position: RoutePoint
    destination: RoutePoint
    monitoring_waypoints: List[RoutePoint]
    intermediate_path_points: List[RoutePoint]
    path_metrics: Dict[str, Any]
    validation: Dict[str, Any]
    static_obstacles: List[StaticObstacleSpec] = field(default_factory=list)


def _validate_coord_dict(obj: Any, field_name: str) -> tuple[float, float, float]:
    if not isinstance(obj, dict):
        raise RouteValidationError(f"Field '{field_name}' must be a JSON object with x, y, z coordinates.")
    for axis in ("x", "y", "z"):
        if axis not in obj:
            raise RouteValidationError(f"Field '{field_name}' is missing required coordinate '{axis}'.")
        val = obj[axis]
        if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(float(val)):
            raise RouteValidationError(f"Coordinate '{axis}' in '{field_name}' must be a finite number.")
    return float(obj["x"]), float(obj["y"]), float(obj["z"])


def load_global_route(route_path: str | Path) -> GlobalRoute:
    """Load, validate, and parse a route JSON produced by the global planner."""
    path = Path(route_path)
    if not path.exists():
        raise FileNotFoundError(f"Global route file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise RouteValidationError(f"Malformed JSON in route file '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise RouteValidationError("Root of global route JSON must be an object.")

    required_fields = [
        "start_position",
        "destination",
        "monitoring_waypoints",
        "intermediate_path_points",
        "path_metrics",
        "validation",
        "coordinate_convention",
    ]
    missing = [req for req in required_fields if req not in data]
    if missing:
        raise RouteValidationError(f"Global route JSON missing required top-level fields: {missing}")

    # Validate planning status
    validation = data["validation"]
    if not isinstance(validation, dict):
        raise RouteValidationError("Field 'validation' must be a JSON object.")
    if not validation.get("is_valid", False):
        raise RouteValidationError(
            f"Global planner marked route as invalid (status={validation.get('status', 'UNKNOWN')})."
        )
    status_str = str(validation.get("status", "SUCCESS")).upper()
    if status_str not in ("SUCCESS", "VALID", "OK", "OPTIMAL", "FEASIBLE"):
        raise RouteValidationError(f"Global planner reported unsuccessful status: {status_str}")
    if validation.get("collision_free") is False:
        raise RouteValidationError("Global planner route failed collision_free validation check.")

    # Validate coordinate convention
    coord_conv = data["coordinate_convention"]
    if not isinstance(coord_conv, dict) or "frame" not in coord_conv:
        raise RouteValidationError("Field 'coordinate_convention' must be an object specifying 'frame'.")

    # Parse start & destination
    sx, sy, sz = _validate_coord_dict(data["start_position"], "start_position")
    start_pt = RoutePoint(x=sx, y=sy, z=sz, is_monitoring=False, waypoint_id="START")

    dx, dy, dz = _validate_coord_dict(data["destination"], "destination")
    dest_pt = RoutePoint(x=dx, y=dy, z=dz, is_monitoring=False, waypoint_id="DEST")

    # Parse ordered monitoring waypoints
    raw_wps = data["monitoring_waypoints"]
    if not isinstance(raw_wps, list) or len(raw_wps) == 0:
        raise RouteValidationError("Field 'monitoring_waypoints' must be a non-empty list.")

    monitoring_waypoints: List[RoutePoint] = []
    for idx, wp in enumerate(raw_wps):
        wx, wy, wz = _validate_coord_dict(wp, f"monitoring_waypoints[{idx}]")
        wp_id = str(wp.get("id", f"WP_{idx + 1}"))
        monitoring_waypoints.append(
            RoutePoint(
                x=wx,
                y=wy,
                z=wz,
                is_monitoring=True,
                waypoint_id=wp_id,
                zone_name=wp.get("zone_name"),
                priority=int(wp.get("priority", 1)),
            )
        )

    # Parse intermediate path points
    raw_path = data["intermediate_path_points"]
    if not isinstance(raw_path, list) or len(raw_path) < 2:
        raise RouteValidationError("Field 'intermediate_path_points' must be a list with at least 2 points.")

    intermediate_points: List[RoutePoint] = []
    for idx, pt in enumerate(raw_path):
        px, py, pz = _validate_coord_dict(pt, f"intermediate_path_points[{idx}]")
        is_mon = bool(pt.get("is_monitoring", False))
        wp_id = pt.get("waypoint_id")
        intermediate_points.append(
            RoutePoint(
                x=px,
                y=py,
                z=pz,
                is_monitoring=is_mon,
                waypoint_id=str(wp_id) if wp_id is not None else None,
            )
        )

    # Validate path metrics
    metrics = data["path_metrics"]
    if not isinstance(metrics, dict) or "planned_path_length_m" not in metrics:
        raise RouteValidationError("Field 'path_metrics' must contain 'planned_path_length_m'.")
    planned_len = metrics["planned_path_length_m"]
    if not isinstance(planned_len, (int, float)) or float(planned_len) <= 0.0:
        raise RouteValidationError("Field 'planned_path_length_m' must be a positive number.")

    # Optional static obstacles exported with the route
    static_obstacles: List[StaticObstacleSpec] = []
    raw_obs = data.get("static_obstacles", [])
    if not isinstance(raw_obs, list):
        raise RouteValidationError("Field 'static_obstacles' must be a list if provided.")
    for idx, obs in enumerate(raw_obs):
        ox, oy, oz = _validate_coord_dict(obs, f"static_obstacles[{idx}]")
        radius = float(obs.get("radius", 1.5))
        if radius <= 0.0:
            raise RouteValidationError(f"Obstacle radius in static_obstacles[{idx}] must be positive.")
        static_obstacles.append(
            StaticObstacleSpec(
                id=str(obs.get("id", f"OBS_{idx + 1}")),
                x=ox,
                y=oy,
                z=oz,
                radius=radius,
            )
        )

    return GlobalRoute(
        mission_id=str(data.get("mission_id", "unnamed_mission")),
        planner_algorithm=str(data.get("planner_algorithm", "GA_2Opt")),
        coordinate_convention=coord_conv,
        start_position=start_pt,
        destination=dest_pt,
        monitoring_waypoints=monitoring_waypoints,
        intermediate_path_points=intermediate_points,
        path_metrics=metrics,
        validation=validation,
        static_obstacles=static_obstacles,
    )
