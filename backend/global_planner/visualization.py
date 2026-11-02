"""Plotting and visualization of planned UAV routes and GA fitness convergence.

Generates publication-quality 2D trajectory maps with obstacle clearance zones
and generation-by-generation optimization convergence plots using Matplotlib.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

# Configure headless backend and temporary config directory before importing pyplot
os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl_cache")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

from backend.global_planner.environment import Environment, Waypoint
from backend.global_planner.obstacle_manager import CircularObstacle, RectangularObstacle


class Visualizer:
    """Renders 2D mission environments, obstacles, planned paths, and fitness trends."""

    def __init__(self, environment: Environment):
        self.env = environment

    def plot_route(
        self,
        path_points: Sequence[Tuple[float, float]],
        ordered_waypoints: Sequence[Waypoint],
        output_path: str | Path,
        title: str = "UAV Global Route Planning - GA with 2-Opt & Obstacle-Aware A*",
    ) -> None:
        """Plot the complete 2D environment, obstacles, waypoints, and the planned path."""
        fig, ax = plt.subplots(figsize=(10, 10), dpi=150)

        # Set bounds and aspect ratio
        margin_x = (self.env.x_max - self.env.x_min) * 0.05
        margin_y = (self.env.y_max - self.env.y_min) * 0.05
        ax.set_xlim(self.env.x_min - margin_x, self.env.x_max + margin_x)
        ax.set_ylim(self.env.y_min - margin_y, self.env.y_max + margin_y)
        ax.set_aspect("equal")
        ax.grid(True, linestyle="--", alpha=0.5)

        # Draw environment boundary box
        env_rect = Rectangle(
            (self.env.x_min, self.env.y_min),
            self.env.x_max - self.env.x_min,
            self.env.y_max - self.env.y_min,
            fill=False,
            edgecolor="black",
            linewidth=1.5,
            linestyle="-",
            label="Map Boundary",
        )
        ax.add_patch(env_rect)

        # Draw obstacles and clearance zones
        first_circ = True
        first_rect = True
        first_clearance = True

        for obs in self.env.obstacle_manager.obstacles:
            clr = self.env.safety_clearance
            if isinstance(obs, CircularObstacle):
                # Clearance circle
                if clr > 0:
                    c_clear = Circle(
                        (obs.x, obs.y),
                        obs.radius + clr,
                        facecolor="salmon",
                        alpha=0.25,
                        edgecolor="red",
                        linestyle="--",
                        linewidth=1.0,
                        label="Safety Clearance" if first_clearance else None,
                    )
                    ax.add_patch(c_clear)
                    first_clearance = False

                # Obstacle circle
                c_obs = Circle(
                    (obs.x, obs.y),
                    obs.radius,
                    facecolor="firebrick" if not obs.is_dynamic else "darkorange",
                    edgecolor="black",
                    linewidth=1.2,
                    label="Obstacle" if first_circ else None,
                )
                ax.add_patch(c_obs)
                first_circ = False

            elif isinstance(obs, RectangularObstacle):
                # Clearance rectangle
                if clr > 0:
                    r_clear = Rectangle(
                        (obs.x_min - clr, obs.y_min - clr),
                        (obs.x_max - obs.x_min) + 2 * clr,
                        (obs.y_max - obs.y_min) + 2 * clr,
                        facecolor="salmon",
                        alpha=0.25,
                        edgecolor="red",
                        linestyle="--",
                        linewidth=1.0,
                        label="Safety Clearance" if first_clearance else None,
                    )
                    ax.add_patch(r_clear)
                    first_clearance = False

                # Obstacle rectangle
                r_obs = Rectangle(
                    (obs.x_min, obs.y_min),
                    obs.x_max - obs.x_min,
                    obs.y_max - obs.y_min,
                    facecolor="firebrick" if not obs.is_dynamic else "darkorange",
                    edgecolor="black",
                    linewidth=1.2,
                    label="Obstacle" if first_rect and first_circ else None,
                )
                ax.add_patch(r_obs)
                first_rect = False

        # Plot continuous A* flight trajectory
        if path_points:
            xs = [p[0] for p in path_points]
            ys = [p[1] for p in path_points]
            ax.plot(
                xs,
                ys,
                color="navy",
                linewidth=2.5,
                linestyle="-",
                label="Optimized Global Route",
                zorder=4,
            )

        # Plot Start point
        ax.scatter(
            [self.env.start.x],
            [self.env.start.y],
            color="limegreen",
            edgecolors="black",
            s=160,
            marker="s",
            zorder=6,
            label="Start Position",
        )
        ax.text(
            self.env.start.x,
            self.env.start.y + 2.0,
            "START",
            fontweight="bold",
            fontsize=9,
            ha="center",
            va="bottom",
            color="darkgreen",
        )

        # Plot Destination point
        ax.scatter(
            [self.env.destination.x],
            [self.env.destination.y],
            color="crimson",
            edgecolors="black",
            s=180,
            marker="*",
            zorder=6,
            label="Destination",
        )
        ax.text(
            self.env.destination.x,
            self.env.destination.y + 2.0,
            "DEST",
            fontweight="bold",
            fontsize=9,
            ha="center",
            va="bottom",
            color="darkred",
        )

        # Plot Monitoring Waypoints in their visited order
        if ordered_waypoints:
            wp_x = [wp.x for wp in ordered_waypoints]
            wp_y = [wp.y for wp in ordered_waypoints]
            ax.scatter(
                wp_x,
                wp_y,
                color="deepskyblue",
                edgecolors="navy",
                s=120,
                marker="o",
                zorder=5,
                label="Monitoring Waypoints",
            )

            for order_idx, wp in enumerate(ordered_waypoints, 1):
                ax.text(
                    wp.x,
                    wp.y + 1.8,
                    f"#{order_idx}\n({wp.id})",
                    fontsize=8,
                    ha="center",
                    va="bottom",
                    fontweight="bold",
                    color="darkblue",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7, edgecolor="none"),
                )

        ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel("X Coordinate (meters)", fontsize=10)
        ax.set_ylabel("Y Coordinate (meters)", fontsize=10)
        ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0)

        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        fig.savefig(out_file, dpi=150, bbox_inches="tight")
        plt.close(fig)

    def plot_fitness_history(
        self,
        cost_history: Sequence[float],
        fitness_history: Sequence[float],
        output_path: str | Path,
        title: str = "GA Convergence History with 2-Opt Refinement",
    ) -> None:
        """Plot cost and fitness evolution across generations."""
        fig, ax1 = plt.subplots(figsize=(9, 5), dpi=150)

        gens = list(range(len(cost_history)))

        color = "tab:blue"
        ax1.set_xlabel("Generation", fontsize=10)
        ax1.set_ylabel("Best Route Cost (Distance in meters)", color=color, fontsize=10)
        line1 = ax1.plot(gens, cost_history, color=color, linewidth=2, label="Best Cost (m)")
        ax1.tick_params(axis="y", labelcolor=color)
        ax1.grid(True, linestyle="--", alpha=0.5)

        # Secondary y-axis for fitness (1 / (1 + cost))
        ax2 = ax1.twinx()
        color = "tab:orange"
        ax2.set_ylabel("Fitness (1 / (1 + cost))", color=color, fontsize=10)
        line2 = ax2.plot(
            gens, fitness_history, color=color, linewidth=1.5, linestyle="--", label="Fitness"
        )
        ax2.tick_params(axis="y", labelcolor=color)

        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc="upper right")

        ax1.set_title(title, fontsize=12, fontweight="bold", pad=12)

        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        fig.savefig(out_file, dpi=150, bbox_inches="tight")
        plt.close(fig)
