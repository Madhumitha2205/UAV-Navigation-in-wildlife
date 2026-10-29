"""Monitoring waypoint generation and coverage pattern algorithms.

Supports user-defined waypoints and automatic lawnmower / Snake-Grid
coverage patterns for systematic wildlife surveillance.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from backend.global_planner.environment import Environment, Waypoint


class WaypointGenerator:
    """Generates and filters surveillance waypoints for UAV wildlife monitoring."""

    def __init__(self, environment: Environment):
        self.env = environment

    def generate_snake_grid(
        self,
        region_bounds: Optional[Tuple[float, float, float, float]] = None,
        step_x: float = 20.0,
        step_y: float = 20.0,
        altitude: float = 10.0,
        importance_weight: float = 1.0,
        prefix: str = "wp",
    ) -> List[Waypoint]:
        """Generate a snake-like / lawnmower coverage pattern.

        Coverage region dimensions (Lx = x_max - x_min, Ly = y_max - y_min) and grid
        spacings (step_x, step_y) dictate the total candidate count:
            cols = floor(Lx / step_x) + 1
            rows = floor(Ly / step_y) + 1
            Candidate count = cols * rows.

        Alternating row traversal (even rows left->right, odd rows right->left)
        minimizes total inter-waypoint transit distance. Any points colliding with
        obstacles or safety clearance zones are strictly excluded.
        """
        if region_bounds is None:
            # Leave a default margin inside environment bounds
            margin = max(self.env.safety_clearance * 2.0, 5.0)
            x_min = self.env.x_min + margin
            x_max = self.env.x_max - margin
            y_min = self.env.y_min + margin
            y_max = self.env.y_max - margin
        else:
            x_min, x_max, y_min, y_max = region_bounds

        if x_max <= x_min or y_max <= y_min:
            raise ValueError(f"Invalid region bounds for waypoint generation: [{x_min}, {x_max}, {y_min}, {y_max}]")
        if step_x <= 0 or step_y <= 0:
            raise ValueError(f"Grid steps must be positive: step_x={step_x}, step_y={step_y}")

        num_y = int(math.floor((y_max - y_min) / step_y)) + 1
        num_x = int(math.floor((x_max - x_min) / step_x)) + 1

        waypoints: List[Waypoint] = []
        counter = 1

        for r in range(num_y):
            cy = y_min + r * step_y
            cols = list(range(num_x))
            if r % 2 == 1:
                cols.reverse()  # Alternate direction for snake/boustrophedon path

            for c in cols:
                cx = x_min + c * step_x

                # Collision and boundary check
                if not self.env.is_valid_position(cx, cy, clearance=self.env.safety_clearance):
                    continue

                wp = Waypoint(
                    id=f"{prefix}_{counter:02d}",
                    x=cx,
                    y=cy,
                    altitude=altitude,
                    importance_weight=importance_weight,
                    is_mandatory=True,
                )
                waypoints.append(wp)
                counter += 1

        return waypoints

    @staticmethod
    def deduplicate_waypoints(
        waypoints: Sequence[Waypoint],
        tolerance: float = 0.5,
    ) -> List[Waypoint]:
        """Remove duplicate waypoints that share IDs or are closer than tolerance."""
        unique: List[Waypoint] = []
        seen_ids = set()

        for wp in waypoints:
            if wp.id in seen_ids:
                continue

            # Check Euclidean distance to existing accepted waypoints
            is_dup = False
            for accepted in unique:
                if math.hypot(wp.x - accepted.x, wp.y - accepted.y) < tolerance:
                    is_dup = True
                    break

            if not is_dup:
                seen_ids.add(wp.id)
                unique.append(wp)

        return unique

    def filter_valid_waypoints(self, waypoints: Sequence[Waypoint]) -> List[Waypoint]:
        """Filter out waypoints outside map boundaries or violating obstacle clearance."""
        valid: List[Waypoint] = []
        for wp in waypoints:
            if self.env.is_valid_position(wp.x, wp.y, clearance=self.env.safety_clearance):
                valid.append(wp)
        return valid

    @staticmethod
    def get_snake_order_indices(waypoints: Sequence[Waypoint]) -> List[int]:
        """Produce permutation indices ordered by a spatial snake traversal heuristic.

        Sorts primarily by discretized Y buckets and secondarily by alternating X.
        Used to seed the Genetic Algorithm initial population.
        """
        if not waypoints:
            return []

        # Find min/max Y to group into rows
        coords = [(i, wp.x, wp.y) for i, wp in enumerate(waypoints)]
        min_y = min(c[2] for c in coords)
        max_y = max(c[2] for c in coords)
        span_y = max(1.0, max_y - min_y)

        # Estimate row count based on number of waypoints
        row_count = max(2, int(math.ceil(math.sqrt(len(waypoints)))))
        row_height = span_y / row_count

        def sort_key(item: Tuple[int, float, float]) -> Tuple[int, float]:
            idx, x, y = item
            row_idx = min(row_count - 1, int((y - min_y) / (row_height + 1e-9)))
            # Alternate X order: even row left-to-right, odd row right-to-left
            adjusted_x = x if (row_idx % 2 == 0) else -x
            return (row_idx, adjusted_x)

        sorted_items = sorted(coords, key=sort_key)
        return [item[0] for item in sorted_items]
