"""Fitness evaluation and pairwise obstacle-aware distance caching.

Computes exact obstacle-aware route costs using precomputed A* path lengths,
enforcing mandatory waypoint coverage and severe collision/infeasibility penalties.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple
import numpy as np

from backend.global_planner.environment import Environment, Waypoint
from backend.global_planner.grid_pathfinder import GridPathfinder, PathResult


class RouteFitnessCalculator:
    """Evaluates the objective cost and fitness of candidate waypoint sequences.

    Cost Function Formulation:
    -------------------------
    Objective: Minimize total obstacle-aware flight distance (in meters) while
    guaranteeing collision-free navigation and 100% mandatory waypoint coverage.

    Formula:
        Total Cost = ObstacleAwareDistance + Penalty_Missing + Penalty_Infeasible

    Where:
        - ObstacleAwareDistance: Sum of true A* grid path distances connecting
          Start -> Waypoint[0] -> Waypoint[1] -> ... -> Waypoint[N-1] -> Destination.
        - Penalty_Missing: 100,000.0 per missing mandatory waypoint.
        - Penalty_Infeasible: 500,000.0 per unreachable / colliding path segment.

    Limitations:
    - The Genetic Algorithm is a metaheuristic and does not guarantee the global
      mathematical minimum route.
    - True path lengths depend on the discrete grid resolution of the A* search.
    """

    PENALTY_MISSING_WAYPOINT = 100_000.0
    PENALTY_INFEASIBLE_SEGMENT = 500_000.0

    def __init__(
        self,
        environment: Environment,
        pathfinder: GridPathfinder,
        waypoints: Optional[Sequence[Waypoint]] = None,
    ):
        self.env = environment
        self.pathfinder = pathfinder
        self.waypoints: List[Waypoint] = (
            list(waypoints) if waypoints is not None else list(environment.monitoring_waypoints)
        )

        # Mapping: node index -> (id, (x, y))
        # 0: start, 1..N: waypoints, N+1: destination
        self.num_waypoints = len(self.waypoints)
        self.start_idx = 0
        self.dest_idx = self.num_waypoints + 1

        self.node_positions: List[Tuple[float, float]] = [self.env.start.to_tuple_2d()]
        for wp in self.waypoints:
            self.node_positions.append(wp.to_tuple_2d())
        self.node_positions.append(self.env.destination.to_tuple_2d())

        # Precomputed pairwise distance matrix: (N+2) x (N+2)
        total_nodes = len(self.node_positions)
        self.dist_matrix = np.full((total_nodes, total_nodes), float("inf"), dtype=float)
        self.path_matrix: Dict[Tuple[int, int], PathResult] = {}

        self._precompute_distance_matrix()

    def _precompute_distance_matrix(self) -> None:
        """Precompute all pairwise A* obstacle-aware paths between nodes."""
        total_nodes = len(self.node_positions)
        for i in range(total_nodes):
            self.dist_matrix[i, i] = 0.0

        for i in range(total_nodes):
            p1 = self.node_positions[i]
            for j in range(i + 1, total_nodes):
                p2 = self.node_positions[j]

                # A* search
                result = self.pathfinder.find_path(p1, p2, use_cache=True)
                self.path_matrix[(i, j)] = result

                # Reverse path for symmetry
                if result.success:
                    rev_points = list(reversed(result.path_points))
                    rev_result = PathResult(
                        success=True,
                        path_points=rev_points,
                        length=result.length,
                        nodes_expanded=result.nodes_expanded,
                    )
                    self.path_matrix[(j, i)] = rev_result
                    self.dist_matrix[i, j] = result.length
                    self.dist_matrix[j, i] = result.length
                else:
                    self.path_matrix[(j, i)] = result
                    self.dist_matrix[i, j] = float("inf")
                    self.dist_matrix[j, i] = float("inf")

    def get_segment_path(self, from_node: int, to_node: int) -> PathResult:
        """Return the precomputed A* path result between two node indices."""
        return self.path_matrix.get(
            (from_node, to_node),
            PathResult(
                success=False,
                path_points=[],
                length=float("inf"),
                error_message="Path not in matrix",
            ),
        )

    def evaluate_chromosome(
        self,
        chromosome: Sequence[int],
    ) -> Tuple[float, bool, Dict[str, float]]:
        """Evaluate a chromosome permutation of monitoring waypoint indices.

        Args:
            chromosome: Sequence of waypoint indices (0 to num_waypoints - 1).

        Returns:
            (total_cost, is_feasible, metrics_dict)
        """
        # Node index mapping: waypoint index k maps to node index (k + 1)
        # Sequence is: start_idx (0) -> (c_0 + 1) -> (c_1 + 1) -> ... -> dest_idx
        visited_nodes = [self.start_idx] + [k + 1 for k in chromosome] + [self.dest_idx]

        total_length = 0.0
        infeasible_segments = 0

        for i in range(len(visited_nodes) - 1):
            n_from = visited_nodes[i]
            n_to = visited_nodes[i + 1]
            seg_dist = self.dist_matrix[n_from, n_to]

            if math.isinf(seg_dist):
                infeasible_segments += 1
                # Fall back to Euclidean distance + huge penalty for continuity
                p_from = self.node_positions[n_from]
                p_to = self.node_positions[n_to]
                total_length += math.hypot(p_to[0] - p_from[0], p_to[1] - p_from[1])
            else:
                total_length += seg_dist

        # Check coverage
        unique_visited_waypoints = set(chromosome)
        missing_count = self.num_waypoints - len(unique_visited_waypoints)

        penalty = (
            missing_count * self.PENALTY_MISSING_WAYPOINT
            + infeasible_segments * self.PENALTY_INFEASIBLE_SEGMENT
        )

        total_cost = total_length + penalty
        is_feasible = (missing_count == 0) and (infeasible_segments == 0)

        metrics = {
            "path_length": total_length,
            "missing_waypoints": float(missing_count),
            "infeasible_segments": float(infeasible_segments),
            "total_cost": total_cost,
            "coverage_ratio": (
                (len(unique_visited_waypoints) / self.num_waypoints)
                if self.num_waypoints > 0
                else 1.0
            ),
        }

        return total_cost, is_feasible, metrics

    def cost_to_fitness(self, cost: float) -> float:
        """Convert minimization cost to positive maximization fitness."""
        return 1.0 / (1.0 + max(0.0, cost))
