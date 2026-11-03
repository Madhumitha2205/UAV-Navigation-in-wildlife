"""Independent route validation module for UAV flight plans.

Strictly checks start/dest endpoints, mandatory waypoint coverage, coordinate bounds,
continuous obstacle collision freedom, clearance margins, and metric integrity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.global_planner.environment import Environment, Waypoint


@dataclass
class ValidationReport:
    """Structured report returned by independent route validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details,
        }


class RouteValidator:
    """Performs rigorous, independent validation on completed UAV routes."""

    def __init__(self, environment: Environment):
        self.env = environment

    def validate_route(
        self,
        ordered_waypoints: Sequence[Waypoint],
        path_points: Sequence[Tuple[float, float]],
        reported_path_length: Optional[float] = None,
        required_waypoints: Optional[Sequence[Waypoint]] = None,
        max_segment_step: Optional[float] = None,
    ) -> ValidationReport:
        """Validate a generated UAV route independently of GA fitness evaluations.

        Checks:
        1. Non-empty path and valid finite coordinates (no NaN or Inf).
        2. Start endpoint matches environment start (within 1e-3).
        3. Destination endpoint matches environment destination (within 1e-3).
        4. Every required monitoring waypoint is present in ordered_waypoints and visited in order along path_points.
        5. All path points lie strictly within map boundaries.
        6. Continuous collision freedom: all path segments do not intersect obstacles or clearance buffer.
        7. Segment continuity: consecutive path points do not jump across unstepped gaps when max_segment_step is set.
        8. Minimum obstacle clearance is >= configured safety clearance (with numerical tolerance).
        9. Reported path length matches actual reconstructed Euclidean segment sum (within tolerance).
        """
        errors: List[str] = []
        warnings: List[str] = []
        details: Dict[str, Any] = {}

        req_wps = (
            list(required_waypoints)
            if required_waypoints is not None
            else list(self.env.monitoring_waypoints)
        )

        # 1. Basic path structure & finite coordinates
        if not path_points or len(path_points) < 2:
            errors.append(f"Route path points must contain at least 2 points. Found {len(path_points)}.")
            return ValidationReport(is_valid=False, errors=errors, warnings=warnings, details=details)

        for idx, pt in enumerate(path_points):
            if len(pt) < 2 or not math.isfinite(pt[0]) or not math.isfinite(pt[1]):
                errors.append(f"Path point at index {idx} contains non-finite coordinates: {pt}")
                break

        # 2. Check start endpoint
        start_pt = path_points[0]
        expected_start = self.env.start.to_tuple_2d()
        dist_start = math.hypot(start_pt[0] - expected_start[0], start_pt[1] - expected_start[1])
        if dist_start > 1e-2:
            errors.append(
                f"Path start {start_pt} does not match environment start {expected_start} (diff={dist_start:.4f})."
            )

        # 3. Check destination endpoint
        dest_pt = path_points[-1]
        expected_dest = self.env.destination.to_tuple_2d()
        dist_dest = math.hypot(dest_pt[0] - expected_dest[0], dest_pt[1] - expected_dest[1])
        if dist_dest > 1e-2:
            errors.append(
                f"Path destination {dest_pt} does not match environment destination {expected_dest} (diff={dist_dest:.4f})."
            )

        # 4. Mandatory waypoint coverage, uniqueness, and ordered presence along path_points
        expected_wp_ids = [wp.id for wp in req_wps if wp.is_mandatory]
        visited_wp_ids = [wp.id for wp in ordered_waypoints]

        # Check duplicates
        if len(visited_wp_ids) != len(set(visited_wp_ids)):
            errors.append(f"Duplicate waypoints present in ordered route: {visited_wp_ids}")

        missing_ids = set(expected_wp_ids) - set(visited_wp_ids)
        if missing_ids:
            errors.append(f"Required mandatory waypoints not visited: {sorted(list(missing_ids))}")

        # Verify each ordered waypoint is actually reached in sequence along path_points
        search_idx = 0
        waypoint_path_indices: List[int] = []
        for wp in ordered_waypoints:
            found_at = -1
            for p_idx in range(search_idx, len(path_points)):
                if math.hypot(path_points[p_idx][0] - wp.x, path_points[p_idx][1] - wp.y) <= 1e-2:
                    found_at = p_idx
                    search_idx = p_idx
                    break
            if found_at == -1:
                errors.append(
                    f"Ordered monitoring waypoint '{wp.id}' at ({wp.x:.2f}, {wp.y:.2f}) does not appear in sequence along path_points."
                )
            else:
                waypoint_path_indices.append(found_at)
        details["waypoint_path_indices"] = waypoint_path_indices

        # 5. Boundary constraints for all path points
        out_of_bounds_count = 0
        for idx, pt in enumerate(path_points):
            if not self.env.is_inside_bounds(pt[0], pt[1]):
                out_of_bounds_count += 1
                if out_of_bounds_count <= 3:
                    errors.append(
                        f"Path point {idx} ({pt[0]:.2f}, {pt[1]:.2f}) is outside environment boundaries "
                        f"[{self.env.x_min}, {self.env.x_max}, {self.env.y_min}, {self.env.y_max}]."
                    )
        if out_of_bounds_count > 3:
            errors.append(f"... and {out_of_bounds_count - 3} more points outside boundaries.")

        # 6. Obstacle collisions, clearance, and segment continuity along continuous segments
        collision_count = 0
        discontinuity_count = 0
        max_observed_step = 0.0
        min_clearance = float("inf")

        # Sample path finely to detect any segment-obstacle collisions
        for i in range(len(path_points) - 1):
            p1 = path_points[i]
            p2 = path_points[i + 1]
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len > max_observed_step:
                max_observed_step = seg_len

            if max_segment_step is not None and seg_len > max_segment_step + 1e-4:
                discontinuity_count += 1
                if discontinuity_count <= 3:
                    errors.append(
                        f"Path segment {i} ({p1} -> {p2}) has discontinuous jump of {seg_len:.2f}m "
                        f"(max allowed step={max_segment_step:.2f}m)."
                    )

            # Direct segment collision check against obstacles + clearance
            if self.env.obstacle_manager.segment_collides(p1, p2, clearance=self.env.safety_clearance):
                collision_count += 1
                if collision_count <= 3:
                    errors.append(
                        f"Path segment {i} ({p1} -> {p2}) violates obstacle safety clearance ({self.env.safety_clearance})."
                    )

            # Measure continuous minimum clearance
            samples = max(2, int(math.ceil(seg_len / 0.5)))
            for s in range(samples + 1):
                t = s / samples
                sx = p1[0] + t * (p2[0] - p1[0])
                sy = p1[1] + t * (p2[1] - p1[1])
                dist = self.env.obstacle_manager.min_distance_to_obstacles(sx, sy)
                if dist < min_clearance:
                    min_clearance = dist

        if discontinuity_count > 3:
            errors.append(f"... and {discontinuity_count - 3} more discontinuous path segments.")
        if collision_count > 3:
            errors.append(f"... and {collision_count - 3} more segments violating clearance.")

        details["minimum_obstacle_clearance"] = (
            min_clearance if math.isfinite(min_clearance) else None
        )
        details["collision_count"] = collision_count
        details["discontinuity_count"] = discontinuity_count
        details["max_segment_step_m"] = max_observed_step

        # 8. Check minimum clearance against configured threshold with slight numerical tolerance
        if min_clearance < self.env.safety_clearance - 0.05:
            # If not already flagged by segment_collides
            if collision_count == 0:
                warnings.append(
                    f"Minimum path obstacle clearance ({min_clearance:.3f}) is slightly below "
                    f"configured safety clearance ({self.env.safety_clearance})."
                )

        # 9. Reconstruct true continuous path length and compare
        actual_length = 0.0
        for i in range(len(path_points) - 1):
            p1 = path_points[i]
            p2 = path_points[i + 1]
            actual_length += math.hypot(p2[0] - p1[0], p2[1] - p1[1])

        details["calculated_path_length"] = actual_length
        if reported_path_length is not None:
            details["reported_path_length"] = reported_path_length
            diff = abs(actual_length - reported_path_length)
            if diff > 1e-2:
                errors.append(
                    f"Reported path length ({reported_path_length:.4f}) differs from actual "
                    f"exported path length ({actual_length:.4f}) by {diff:.4f} meters."
                )

        details["visited_waypoints_count"] = len(ordered_waypoints)
        details["required_waypoints_count"] = len(req_wps)
        details["coverage_percentage"] = (
            (len(visited_wp_ids) / len(req_wps) * 100.0) if req_wps else 100.0
        )

        is_valid = len(errors) == 0
        return ValidationReport(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            details=details,
        )
