"""Obstacle-aware A* pathfinding on discretized 2D occupancy grids.

Implements 8-connected A* search with strict corner-cutting prevention,
admissible heuristics, continuous coordinate conversion, and pairwise caching.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

from backend.global_planner.environment import Environment


@dataclass
class PathResult:
    """Outcome of an A* path search."""

    success: bool
    path_points: List[Tuple[float, float]]
    length: float
    nodes_expanded: int = 0
    error_message: Optional[str] = None


class GridPathfinder:
    """Computes obstacle-aware paths between 2D coordinates on an occupancy grid.

    Grid Resolution Limitations & Collision Assumptions:
    - The environment continuous coordinate plane is discretized into square grid
      cells of size `grid_resolution`.
    - Obstacles are inflated by the safety clearance buffer. Any cell containing
      or touching the inflated obstacle geometry is marked as occupied.
    - Diagonal moves cost sqrt(2) * resolution. Corner-cutting is strictly prohibited:
      a diagonal move from (r, c) to (r+dr, c+dc) is permitted only if BOTH adjacent
      orthogonal cells (r+dr, c) and (r, c+dc) are free.
    - A smaller grid resolution yields smoother, more optimal paths around curved
      obstacles at the cost of O((W/res)*(H/res)) memory and search time.
    """

    def __init__(self, environment: Environment):
        self.env = environment
        self.grid_res = environment.grid_resolution
        self.clearance = environment.safety_clearance

        # Build occupancy grid
        self.occupancy, self.width_cells, self.height_cells = (
            self.env.obstacle_manager.rasterize_grid(
                x_min=self.env.x_min,
                x_max=self.env.x_max,
                y_min=self.env.y_min,
                y_max=self.env.y_max,
                grid_resolution=self.grid_res,
                clearance=self.clearance,
            )
        )

        # Cache of pairwise path results keyed by (p1_rounded, p2_rounded)
        self._path_cache: Dict[Tuple[Tuple[float, float], Tuple[float, float]], PathResult] = {}

    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """Convert continuous world coordinates to nearest integer grid (row, col)."""
        col = int(round((x - self.env.x_min) / self.grid_res))
        row = int(round((y - self.env.y_min) / self.grid_res))
        return (row, col)

    def grid_to_world(self, row: int, col: int) -> Tuple[float, float]:
        """Convert integer grid (row, col) to continuous world coordinates."""
        x = self.env.x_min + col * self.grid_res
        y = self.env.y_min + row * self.grid_res
        return (x, y)

    def is_cell_free(self, row: int, col: int) -> bool:
        """Return True if (row, col) is within grid bounds and not occupied."""
        if 0 <= row < self.height_cells and 0 <= col < self.width_cells:
            return not self.occupancy[row, col]
        return False

    def find_path(
        self,
        start_pt: Tuple[float, float],
        goal_pt: Tuple[float, float],
        use_cache: bool = True,
    ) -> PathResult:
        """Find an obstacle-aware A* path between two continuous 2D coordinates."""
        key = (
            (round(start_pt[0], 3), round(start_pt[1], 3)),
            (round(goal_pt[0], 3), round(goal_pt[1], 3)),
        )
        if use_cache and key in self._path_cache:
            return self._path_cache[key]

        start_r, start_c = self.world_to_grid(start_pt[0], start_pt[1])
        goal_r, goal_c = self.world_to_grid(goal_pt[0], goal_pt[1])

        # Verify start and goal grid coordinates
        if not (0 <= start_r < self.height_cells and 0 <= start_c < self.width_cells):
            res = PathResult(
                success=False,
                path_points=[],
                length=float("inf"),
                error_message=f"Start point {start_pt} out of grid bounds.",
            )
            if use_cache:
                self._path_cache[key] = res
            return res

        if not (0 <= goal_r < self.height_cells and 0 <= goal_c < self.width_cells):
            res = PathResult(
                success=False,
                path_points=[],
                length=float("inf"),
                error_message=f"Goal point {goal_pt} out of grid bounds.",
            )
            if use_cache:
                self._path_cache[key] = res
            return res

        if self.occupancy[start_r, start_c]:
            res = PathResult(
                success=False,
                path_points=[],
                length=float("inf"),
                error_message=f"Start point {start_pt} is inside an obstacle or clearance buffer.",
            )
            if use_cache:
                self._path_cache[key] = res
            return res

        if self.occupancy[goal_r, goal_c]:
            res = PathResult(
                success=False,
                path_points=[],
                length=float("inf"),
                error_message=f"Goal point {goal_pt} is inside an obstacle or clearance buffer.",
            )
            if use_cache:
                self._path_cache[key] = res
            return res

        # Trivial case: start == goal
        if (start_r, start_c) == (goal_r, goal_c):
            res = PathResult(
                success=True,
                path_points=[start_pt, goal_pt],
                length=math.hypot(goal_pt[0] - start_pt[0], goal_pt[1] - start_pt[1]),
                nodes_expanded=0,
            )
            if use_cache:
                self._path_cache[key] = res
            return res

        # 8-connected movements: (dr, dc, step_cost)
        sqrt2 = math.sqrt(2.0) * self.grid_res
        straight = 1.0 * self.grid_res
        directions = [
            (0, 1, straight, False),
            (0, -1, straight, False),
            (1, 0, straight, False),
            (-1, 0, straight, False),
            (1, 1, sqrt2, True),
            (1, -1, sqrt2, True),
            (-1, 1, sqrt2, True),
            (-1, -1, sqrt2, True),
        ]

        def heuristic(r: int, c: int) -> float:
            # Octile or Euclidean distance
            dx = abs(c - goal_c) * self.grid_res
            dy = abs(r - goal_r) * self.grid_res
            # Euclidean distance is strictly admissible
            return math.hypot(dx, dy)

        # Priority queue entries: (f_score, h_score, (r, c))
        open_set: List[Tuple[float, float, Tuple[int, int]]] = []
        h_start = heuristic(start_r, start_c)
        heapq.heappush(open_set, (h_start, h_start, (start_r, start_c)))

        g_score: Dict[Tuple[int, int], float] = {(start_r, start_c): 0.0}
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        closed_set = set()
        nodes_expanded = 0

        path_found = False

        while open_set:
            _, _, current = heapq.heappop(open_set)
            if current in closed_set:
                continue

            closed_set.add(current)
            nodes_expanded += 1

            if current == (goal_r, goal_c):
                path_found = True
                break

            curr_r, curr_c = current
            curr_g = g_score[current]

            for dr, dc, cost, is_diagonal in directions:
                nr, nc = curr_r + dr, curr_c + dc

                if not (0 <= nr < self.height_cells and 0 <= nc < self.width_cells):
                    continue

                if self.occupancy[nr, nc]:
                    continue

                # Strict corner-cutting check for diagonal moves:
                # Both orthogonal adjacent cells must be unblocked!
                if is_diagonal:
                    if self.occupancy[curr_r + dr, curr_c] or self.occupancy[curr_r, curr_c + dc]:
                        continue

                tentative_g = curr_g + cost
                neighbor = (nr, nc)

                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    h = heuristic(nr, nc)
                    heapq.heappush(open_set, (tentative_g + h, h, neighbor))

        if not path_found:
            res = PathResult(
                success=False,
                path_points=[],
                length=float("inf"),
                nodes_expanded=nodes_expanded,
                error_message=f"No collision-free path exists between {start_pt} and {goal_pt}.",
            )
            if use_cache:
                self._path_cache[key] = res
            return res

        # Reconstruct path from goal back to start
        current = (goal_r, goal_c)
        grid_path = [current]
        while current in came_from:
            current = came_from[current]
            grid_path.append(current)
        grid_path.reverse()

        # Convert grid points to continuous world points
        raw_points: List[Tuple[float, float]] = [start_pt]
        for r, c in grid_path[1:-1]:
            wx, wy = self.grid_to_world(r, c)
            raw_points.append((wx, wy))
        raw_points.append(goal_pt)

        # Smooth / simplify colinear points
        simplified_points = self._simplify_path(raw_points)

        # Compute total continuous path length
        path_length = 0.0
        for i in range(len(simplified_points) - 1):
            p1 = simplified_points[i]
            p2 = simplified_points[i + 1]
            path_length += math.hypot(p2[0] - p1[0], p2[1] - p1[1])

        res = PathResult(
            success=True,
            path_points=simplified_points,
            length=path_length,
            nodes_expanded=nodes_expanded,
        )
        if use_cache:
            self._path_cache[key] = res
        return res

    def _simplify_path(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Remove redundant intermediate points that are collinear."""
        if len(points) <= 2:
            return points

        result = [points[0]]
        for i in range(1, len(points) - 1):
            p_prev = result[-1]
            p_curr = points[i]
            p_next = points[i + 1]

            # Vector cross product to test collinearity
            v1 = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
            v2 = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])
            cross = v1[0] * v2[1] - v1[1] * v2[0]

            # Also ensure vectors point in same direction (dot > 0)
            dot = v1[0] * v2[0] + v1[1] * v2[1]

            if abs(cross) > 1e-6 or dot <= 0:
                result.append(p_curr)

        result.append(points[-1])
        return result

    def clear_cache(self) -> None:
        """Clear cached paths."""
        self._path_cache.clear()
