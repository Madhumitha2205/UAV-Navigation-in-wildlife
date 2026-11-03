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

    # Verify start and destination endpoints match intermediate_path_points[0] and [-1]
    p0 = intermediate_points[0]
    p_end = intermediate_points[-1]
    if math.hypot(p0.x - start_pt.x, p0.y - start_pt.y) > 0.1 or abs(p0.z - start_pt.z) > 0.5:
        raise RouteValidationError(
            f"First intermediate_path_point ({p0.x}, {p0.y}, {p0.z}) does not match start_position "
            f"({start_pt.x}, {start_pt.y}, {start_pt.z})."
        )
    if math.hypot(p_end.x - dest_pt.x, p_end.y - dest_pt.y) > 0.1 or abs(p_end.z - dest_pt.z) > 0.5:
        raise RouteValidationError(
            f"Last intermediate_path_point ({p_end.x}, {p_end.y}, {p_end.z}) does not match destination "
            f"({dest_pt.x}, {dest_pt.y}, {dest_pt.z})."
        )

    # Verify every monitoring waypoint appears in sequence in intermediate_path_points
    search_idx = 0
    for wp in monitoring_waypoints:
        found_idx = -1
        for p_idx in range(search_idx, len(intermediate_points)):
            pt = intermediate_points[p_idx]
            if math.hypot(pt.x - wp.x, pt.y - wp.y) <= 0.1 and abs(pt.z - wp.z) <= 0.5:
                found_idx = p_idx
                # Ensure monitoring flag and waypoint_id are set on the matched path point
                pt.is_monitoring = True
                if pt.waypoint_id is None:
                    pt.waypoint_id = wp.waypoint_id
                search_idx = p_idx
                break
        if found_idx == -1:
            raise RouteValidationError(
                f"Monitoring waypoint '{wp.waypoint_id}' ({wp.x}, {wp.y}, {wp.z}) is missing or out of order "
                "in 'intermediate_path_points'."
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


def convert_planned_route_dict_to_controller_dict(
    planned_data: Dict[str, Any],
    mission_id: str = "wildlife_monitoring_generated_route",
    static_obstacles: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Convert Part 1 Global Planner JSON dict (`planned_route.json`) to Part 2 Controller JSON dict (`controller_route.json`).

    Validates that the source planner output is well-formed, valid, collision-free,
    and preserves all monitoring waypoints, intermediate path points, and truthful metrics.
    """
    if not isinstance(planned_data, dict):
        raise RouteValidationError("Planner route data must be a JSON object.")

    req_planner_fields = [
        "status",
        "planner",
        "coordinate_frame",
        "start",
        "destination",
        "ordered_monitoring_waypoints",
        "path_points",
        "metrics",
        "validation",
    ]
    missing = [k for k in req_planner_fields if k not in planned_data]
    if missing:
        raise RouteValidationError(f"Planner route JSON missing required fields: {missing}")

    status_str = str(planned_data.get("status", "")).upper()
    val_block = planned_data.get("validation", {})
    if not isinstance(val_block, dict):
        raise RouteValidationError("Planner route 'validation' field must be a JSON object.")

    is_valid = bool(val_block.get("is_valid", False)) and (status_str == "SUCCESS")
    val_errors = val_block.get("errors", [])
    metrics_block = planned_data.get("metrics", {})
    if not isinstance(metrics_block, dict):
        raise RouteValidationError("Planner route 'metrics' field must be a JSON object.")

    collision_count = int(metrics_block.get("collision_count", 0))
    collision_free = is_valid and (collision_count == 0)

    if not is_valid or not collision_free:
        raise RouteValidationError(
            f"Refusing to convert invalid or colliding planned route (status={status_str}, "
            f"is_valid={val_block.get('is_valid')}, collision_count={collision_count}, errors={val_errors})."
        )

    def _extract_xyz_from_planner_pt(pt_obj: Any, name: str) -> tuple[float, float, float]:
        if not isinstance(pt_obj, dict):
            raise RouteValidationError(f"Planner point '{name}' must be an object.")
        if "x" not in pt_obj or "y" not in pt_obj:
            raise RouteValidationError(f"Planner point '{name}' missing 'x' or 'y'.")
        z_val = pt_obj.get("altitude", pt_obj.get("z"))
        if z_val is None:
            raise RouteValidationError(f"Planner point '{name}' missing 'altitude' (or 'z').")
        return _validate_coord_dict({"x": pt_obj["x"], "y": pt_obj["y"], "z": z_val}, name)

    sx, sy, sz = _extract_xyz_from_planner_pt(planned_data["start"], "start")
    dx, dy, dz = _extract_xyz_from_planner_pt(planned_data["destination"], "destination")

    raw_wps = planned_data["ordered_monitoring_waypoints"]
    if not isinstance(raw_wps, list) or len(raw_wps) == 0:
        raise RouteValidationError("Planner route 'ordered_monitoring_waypoints' must be a non-empty list.")

    ctrl_wps: List[Dict[str, Any]] = []
    for idx, wp in enumerate(raw_wps):
        wx, wy, wz = _extract_xyz_from_planner_pt(wp, f"ordered_monitoring_waypoints[{idx}]")
        wp_id = str(wp.get("id", f"WP_{idx + 1}"))
        order_num = int(wp.get("order", idx + 1))
        ctrl_wps.append(
            {
                "id": wp_id,
                "order": order_num,
                "x": round(wx, 4),
                "y": round(wy, 4),
                "z": round(wz, 2),
                "zone_name": str(wp.get("zone_name", wp_id)),
                "priority": int(wp.get("priority", 1)),
                "importance_weight": float(wp.get("importance_weight", 1.0)),
            }
        )

    raw_pts = planned_data["path_points"]
    if not isinstance(raw_pts, list) or len(raw_pts) < 2:
        raise RouteValidationError("Planner route 'path_points' must contain at least 2 points.")

    parsed_pts: List[tuple[float, float, float, Dict[str, Any]]] = []
    for idx, pt in enumerate(raw_pts):
        px, py, pz = _extract_xyz_from_planner_pt(pt, f"path_points[{idx}]")
        parsed_pts.append((px, py, pz, pt))

    # Match ordered monitoring waypoints sequentially along path_points
    wp_index_map: Dict[int, str] = {}
    search_idx = 0
    for wp_item in ctrl_wps:
        found_idx = -1
        for p_idx in range(search_idx, len(parsed_pts)):
            px, py, _, _ = parsed_pts[p_idx]
            if math.hypot(px - wp_item["x"], py - wp_item["y"]) <= 1e-2:
                found_idx = p_idx
                search_idx = p_idx
                break
        if found_idx == -1:
            raise RouteValidationError(
                f"Monitoring waypoint '{wp_item['id']}' ({wp_item['x']}, {wp_item['y']}) "
                "was not found in sequence along planner 'path_points'."
            )
        wp_index_map[found_idx] = wp_item["id"]

    ctrl_path_points: List[Dict[str, Any]] = []
    actual_length = 0.0
    for idx, (px, py, pz, orig_pt) in enumerate(parsed_pts):
        if idx > 0:
            prev_x, prev_y, prev_z, _ = parsed_pts[idx - 1]
            actual_length += math.sqrt((px - prev_x) ** 2 + (py - prev_y) ** 2 + (pz - prev_z) ** 2)

        if idx in wp_index_map:
            is_mon = True
            wp_id: Optional[str] = wp_index_map[idx]
        else:
            is_mon = bool(orig_pt.get("is_monitoring", False))
            raw_id = orig_pt.get("waypoint_id")
            if raw_id in ("START", "DEST"):
                wp_id = raw_id
            elif idx == 0:
                wp_id = "START"
            elif idx == len(parsed_pts) - 1:
                wp_id = "DEST"
            else:
                wp_id = str(raw_id) if raw_id is not None else None

        ctrl_path_points.append(
            {
                "point_index": idx,
                "x": round(px, 4),
                "y": round(py, 4),
                "z": round(pz, 2),
                "is_monitoring": is_mon,
                "waypoint_id": wp_id,
            }
        )

    reported_len = float(metrics_block.get("path_length", actual_length))
    if reported_len <= 0.0:
        raise RouteValidationError(f"Planner route reported non-positive path_length: {reported_len}")

    if abs(reported_len - actual_length) > 0.1:
        raise RouteValidationError(
            f"Planner reported path_length ({reported_len:.4f}m) does not match actual path geometry ({actual_length:.4f}m)."
        )

    controller_payload: Dict[str, Any] = {
        "mission_id": mission_id,
        "planner_algorithm": str(planned_data.get("planner", "GA_2OPT_ASTAR")),
        "source_schema_version": str(planned_data.get("schema_version", "1.0")),
        "coordinate_convention": {
            "frame": "ENU_ALT_UP",
            "source_planner_frame": str(planned_data.get("coordinate_frame", "planner_xy_altitude_up")),
            "units": "metres",
            "axes": {
                "x": "East",
                "y": "North",
                "z": "Altitude_Positive_Up",
            },
        },
        "validation": {
            "is_valid": is_valid,
            "status": status_str,
            "collision_free": collision_free,
            "collision_count": collision_count,
            "minimum_obstacle_clearance_m": metrics_block.get("minimum_obstacle_clearance"),
            "planning_time_sec": float(metrics_block.get("planning_time_seconds", 0.0)),
            "errors": list(val_errors),
            "warnings": list(val_block.get("warnings", [])),
        },
        "start_position": {
            "x": round(sx, 4),
            "y": round(sy, 4),
            "z": round(sz, 2),
        },
        "destination": {
            "x": round(dx, 4),
            "y": round(dy, 4),
            "z": round(dz, 2),
        },
        "monitoring_waypoints": ctrl_wps,
        "intermediate_path_points": ctrl_path_points,
        "path_metrics": {
            "planned_path_length_m": round(actual_length, 4),
            "reported_planner_length_m": round(reported_len, 4),
            "num_monitoring_waypoints": len(ctrl_wps),
            "num_total_points": len(ctrl_path_points),
            "coverage_percentage": float(metrics_block.get("coverage_percentage", 100.0)),
            "generations_completed": int(metrics_block.get("generations_completed", 0)),
            "two_opt_improvements": int(metrics_block.get("two_opt_improvements", 0)),
        },
    }

    if static_obstacles is not None:
        controller_payload["static_obstacles"] = static_obstacles

    return controller_payload


def convert_planned_route_file(
    planned_route_path: str | Path,
    controller_route_path: str | Path,
    mission_id: str = "wildlife_monitoring_generated_route",
    static_obstacles: Optional[List[Dict[str, Any]]] = None,
) -> GlobalRoute:
    """Read `planned_route.json`, convert and write `controller_route.json`, and return validated `GlobalRoute`."""
    src_path = Path(planned_route_path)
    if not src_path.exists():
        raise FileNotFoundError(f"Planner output route file not found: {src_path}")

    try:
        with src_path.open("r", encoding="utf-8") as f:
            planned_data = json.load(f)
    except json.JSONDecodeError as exc:
        raise RouteValidationError(f"Malformed JSON in planner route file '{src_path}': {exc}") from exc

    ctrl_dict = convert_planned_route_dict_to_controller_dict(
        planned_data,
        mission_id=mission_id,
        static_obstacles=static_obstacles,
    )

    dst_path = Path(controller_route_path)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with dst_path.open("w", encoding="utf-8") as f:
        json.dump(ctrl_dict, f, indent=2)

    return load_global_route(dst_path)
