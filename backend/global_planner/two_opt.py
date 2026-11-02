"""2-Opt local search trajectory optimization.

Performs iterative edge-reversal moves to eliminate route self-crossings
and optimize obstacle-aware traversal lengths while strictly preserving feasibility.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from backend.global_planner.config import TwoOptConfig
from backend.global_planner.fitness import RouteFitnessCalculator


class TwoOptOptimizer:
    """Iterative 2-Opt local search optimizer for waypoint permutations.

    Properties:
    - Fixed start and destination endpoints.
    - Preserves all required monitoring waypoint identifiers.
    - Evaluates candidates using obstacle-aware A* distances.
    - Strictly rejects any candidate permutation that introduces collisions or infeasible segments.
    """

    def __init__(
        self,
        fitness_calculator: RouteFitnessCalculator,
        config: Optional[TwoOptConfig] = None,
    ):
        self.calculator = fitness_calculator
        self.config = config if config is not None else TwoOptConfig()

    def optimize(
        self,
        chromosome: List[int],
        current_cost: Optional[float] = None,
    ) -> Tuple[List[int], float, bool]:
        """Apply 2-Opt local search to improve a waypoint permutation.

        Args:
            chromosome: List of waypoint indices.
            current_cost: Optional pre-evaluated cost of the chromosome.

        Returns:
            (optimized_chromosome, final_cost, was_improved)
        """
        n = len(chromosome)
        if n < 4:
            # 2-Opt requires at least 4 nodes (or 2 internal waypoints) to perform a non-trivial reversal
            if current_cost is None:
                current_cost, _, _ = self.calculator.evaluate_chromosome(chromosome)
            return list(chromosome), current_cost, False

        best_route = list(chromosome)
        if current_cost is None:
            best_cost, is_feasible, _ = self.calculator.evaluate_chromosome(best_route)
            if not is_feasible:
                # Do not optimize already infeasible base routes
                return best_route, best_cost, False
        else:
            best_cost = current_cost

        improved = True
        iterations = 0
        overall_improved = False

        while improved and iterations < self.config.max_iterations:
            improved = False
            iterations += 1

            for i in range(n - 1):
                for j in range(i + 1, n):
                    # 2-Opt move: reverse subsequence from i to j inclusive
                    candidate = best_route[:i] + list(reversed(best_route[i : j + 1])) + best_route[j + 1 :]

                    cand_cost, cand_feasible, _ = self.calculator.evaluate_chromosome(candidate)

                    # Only accept if strictly feasible and improves cost beyond threshold
                    if cand_feasible and (cand_cost < best_cost - self.config.improvement_threshold):
                        best_route = candidate
                        best_cost = cand_cost
                        improved = True
                        overall_improved = True
                        break  # First improvement restart
                if improved:
                    break

        return best_route, best_cost, overall_improved
