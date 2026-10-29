"""Permutation-based Genetic Algorithm with Order Crossover (OX) and 2-Opt hybrid optimization.

Solves global TSP-with-obstacles route ordering with fixed start and destination,
Snake-Grid population seeding, elitism, and generation-by-generation tracking.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple
import numpy as np

from backend.global_planner.config import GeneticAlgorithmConfig
from backend.global_planner.fitness import RouteFitnessCalculator
from backend.global_planner.two_opt import TwoOptOptimizer
from backend.global_planner.waypoint_generator import WaypointGenerator


@dataclass
class Individual:
    """Represents a candidate route chromosome and evaluated metrics."""

    chromosome: List[int]
    cost: float
    is_feasible: bool
    metrics: Dict[str, float]


@dataclass
class GAResult:
    """Complete summary of the Genetic Algorithm execution."""

    success: bool
    best_chromosome: List[int]
    best_cost: float
    is_feasible: bool
    fitness_history: List[float]
    best_cost_history: List[float]
    generations_completed: int
    two_opt_improvements: int
    error_message: Optional[str] = None


class GeneticAlgorithm:
    """Permutation Genetic Algorithm with OX Crossover and periodic 2-Opt refinement."""

    def __init__(
        self,
        fitness_calculator: RouteFitnessCalculator,
        config: Optional[GeneticAlgorithmConfig] = None,
        two_opt_optimizer: Optional[TwoOptOptimizer] = None,
    ):
        self.calculator = fitness_calculator
        self.config = config if config is not None else GeneticAlgorithmConfig()
        self.two_opt = (
            two_opt_optimizer
            if two_opt_optimizer is not None
            else TwoOptOptimizer(fitness_calculator)
        )
        self.num_waypoints = fitness_calculator.num_waypoints

        self.rng = random.Random(self.config.random_seed)
        self.np_rng = np.random.RandomState(self.config.random_seed)

    def _create_snake_individual(self, base_order: List[int]) -> List[int]:
        """Create a candidate by lightly perturbing the snake heuristic order."""
        ind = list(base_order)
        # Apply 1 or 2 small random swaps to generate diversity
        num_swaps = self.rng.randint(0, max(1, len(ind) // 4))
        for _ in range(num_swaps):
            i = self.rng.randrange(len(ind))
            j = self.rng.randrange(len(ind))
            ind[i], ind[j] = ind[j], ind[i]
        return ind

    def initialize_population(self) -> List[Individual]:
        """Initialize population with a hybrid of Snake-Grid heuristic and random permutations."""
        population: List[Individual] = []

        if self.num_waypoints == 0:
            return population

        base_snake = WaypointGenerator.get_snake_order_indices(self.calculator.waypoints)
        if not base_snake or len(base_snake) != self.num_waypoints:
            base_snake = list(range(self.num_waypoints))

        snake_count = int(self.config.population_size * self.config.snake_grid_init_ratio)
        random_count = self.config.population_size - snake_count

        # Seed with base snake order first
        cost, feasible, metrics = self.calculator.evaluate_chromosome(base_snake)
        population.append(Individual(list(base_snake), cost, feasible, metrics))

        # Snake variants
        for _ in range(snake_count - 1):
            chromo = self._create_snake_individual(base_snake)
            cost, feasible, metrics = self.calculator.evaluate_chromosome(chromo)
            population.append(Individual(chromo, cost, feasible, metrics))

        # Random permutations
        for _ in range(random_count):
            chromo = list(range(self.num_waypoints))
            self.rng.shuffle(chromo)
            cost, feasible, metrics = self.calculator.evaluate_chromosome(chromo)
            population.append(Individual(chromo, cost, feasible, metrics))

        # Sort by cost ascending (lower cost = better fitness)
        population.sort(key=lambda ind: ind.cost)
        return population

    def tournament_selection(self, population: List[Individual], k: int = 3) -> Individual:
        """Select a parent using k-way tournament selection."""
        candidates = self.rng.sample(population, min(k, len(population)))
        candidates.sort(key=lambda ind: ind.cost)
        return candidates[0]

    def order_crossover(self, parent1: List[int], parent2: List[int]) -> Tuple[List[int], List[int]]:
        """Order Crossover (OX) for permutation chromosomes.

        Preserves relative order and guarantees that all required waypoint indices
        appear exactly once in each child.
        """
        n = len(parent1)
        if n < 2:
            return list(parent1), list(parent2)

        def ox_single(p1: List[int], p2: List[int]) -> List[int]:
            c1 = self.rng.randrange(n)
            c2 = self.rng.randrange(n)
            start_cut = min(c1, c2)
            end_cut = max(c1, c2) + 1

            # Copied segment from parent 1
            segment = p1[start_cut:end_cut]
            in_segment = set(segment)

            child = [None] * n
            child[start_cut:end_cut] = segment

            # Fill remaining spots in order from parent 2 starting after end_cut
            p2_order = p2[end_cut:] + p2[:end_cut]
            fill_candidates = [val for val in p2_order if val not in in_segment]

            fill_idx = 0
            for i in list(range(end_cut, n)) + list(range(0, start_cut)):
                child[i] = fill_candidates[fill_idx]
                fill_idx += 1

            return child

        child1 = ox_single(parent1, parent2)
        child2 = ox_single(parent2, parent1)
        return child1, child2

    def mutate(self, chromosome: List[int]) -> List[int]:
        """Perform swap or inversion mutation on a permutation chromosome."""
        mutated = list(chromosome)
        n = len(mutated)
        if n < 2:
            return mutated

        if self.rng.random() < 0.5:
            # Swap mutation
            i = self.rng.randrange(n)
            j = self.rng.randrange(n)
            mutated[i], mutated[j] = mutated[j], mutated[i]
        else:
            # Inversion mutation
            i = self.rng.randrange(n)
            j = self.rng.randrange(n)
            c1, c2 = min(i, j), max(i, j)
            mutated[c1 : c2 + 1] = reversed(mutated[c1 : c2 + 1])

        return mutated

    def run(self) -> GAResult:
        """Execute the Genetic Algorithm with elitism and periodic 2-Opt local search."""
        if self.num_waypoints == 0:
            return GAResult(
                success=True,
                best_chromosome=[],
                best_cost=0.0,
                is_feasible=True,
                fitness_history=[0.0],
                best_cost_history=[0.0],
                generations_completed=0,
                two_opt_improvements=0,
            )

        population = self.initialize_population()
        best_overall = population[0]

        best_cost_history: List[float] = [best_overall.cost]
        fitness_history: List[float] = [self.calculator.cost_to_fitness(best_overall.cost)]

        generations_without_improvement = 0
        two_opt_improvements_count = 0

        for gen in range(1, self.config.max_generations + 1):
            next_population: List[Individual] = []

            # Elitism: preserve top individuals
            elites = population[: self.config.elite_count]
            for elite in elites:
                next_population.append(
                    Individual(
                        list(elite.chromosome),
                        elite.cost,
                        elite.is_feasible,
                        elite.metrics,
                    )
                )

            # Generate offspring
            while len(next_population) < self.config.population_size:
                p1 = self.tournament_selection(population)
                p2 = self.tournament_selection(population)

                if self.rng.random() < self.config.crossover_probability:
                    c1_chromo, c2_chromo = self.order_crossover(p1.chromosome, p2.chromosome)
                else:
                    c1_chromo, c2_chromo = list(p1.chromosome), list(p2.chromosome)

                if self.rng.random() < self.config.mutation_probability:
                    c1_chromo = self.mutate(c1_chromo)
                if self.rng.random() < self.config.mutation_probability:
                    c2_chromo = self.mutate(c2_chromo)

                # Evaluate children
                cost1, feas1, met1 = self.calculator.evaluate_chromosome(c1_chromo)
                next_population.append(Individual(c1_chromo, cost1, feas1, met1))

                if len(next_population) < self.config.population_size:
                    cost2, feas2, met2 = self.calculator.evaluate_chromosome(c2_chromo)
                    next_population.append(Individual(c2_chromo, cost2, feas2, met2))

            # Periodic 2-Opt optimization on the top candidate slice
            if gen % self.config.two_opt_frequency == 0:
                next_population.sort(key=lambda ind: ind.cost)
                top_count = max(1, int(len(next_population) * self.config.two_opt_candidate_ratio))

                for idx in range(top_count):
                    ind = next_population[idx]
                    if ind.is_feasible:
                        opt_chromo, opt_cost, improved = self.two_opt.optimize(
                            ind.chromosome, current_cost=ind.cost
                        )
                        if improved:
                            two_opt_improvements_count += 1
                            _, opt_feasible, opt_metrics = self.calculator.evaluate_chromosome(opt_chromo)
                            next_population[idx] = Individual(
                                opt_chromo, opt_cost, opt_feasible, opt_metrics
                            )

            # Sort new generation by cost
            next_population.sort(key=lambda ind: ind.cost)
            population = next_population

            current_best = population[0]
            if current_best.cost < best_overall.cost - 1e-4:
                best_overall = current_best
                generations_without_improvement = 0
            else:
                generations_without_improvement += 1

            best_cost_history.append(best_overall.cost)
            fitness_history.append(self.calculator.cost_to_fitness(best_overall.cost))

            # Early stopping check
            if generations_without_improvement >= self.config.patience and best_overall.is_feasible:
                break

        # Final 2-Opt polish on the best overall individual
        if best_overall.is_feasible:
            final_chromo, final_cost, final_improved = self.two_opt.optimize(
                best_overall.chromosome, current_cost=best_overall.cost
            )
            if final_improved:
                two_opt_improvements_count += 1
                _, final_feasible, final_metrics = self.calculator.evaluate_chromosome(final_chromo)
                best_overall = Individual(final_chromo, final_cost, final_feasible, final_metrics)

        success = best_overall.is_feasible
        err_msg = None if success else "GA failed to find a collision-free feasible route covering all waypoints."

        return GAResult(
            success=success,
            best_chromosome=best_overall.chromosome,
            best_cost=best_overall.cost,
            is_feasible=best_overall.is_feasible,
            fitness_history=fitness_history,
            best_cost_history=best_cost_history,
            generations_completed=len(best_cost_history) - 1,
            two_opt_improvements=two_opt_improvements_count,
            error_message=err_msg,
        )
