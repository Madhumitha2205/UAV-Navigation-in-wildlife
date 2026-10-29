"""Comparative Evaluation and Metrics Reporting for Local UAV Navigation.

Compares three required configurations under identical routes, obstacle scenarios, and seeds:
- Configuration A: `BASELINE` (Baseline waypoint navigation without TD3)
- Configuration B: `TD3_NO_SAFETY` (TD3 without the fuzzy safety layer)
- Configuration C: `TD3_WITH_FUZZY_SAFETY` (TD3 with the Adaptive Fuzzy Logic safety layer)

Records actual measured trial outcomes across multiple seeds, computes means and standard
deviations, exports CSV logs + JSON summaries, and generates comparative plots.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
import numpy as np

# Ensure writable Matplotlib cache directory on Windows before importing matplotlib
os.environ.setdefault("MPLCONFIGDIR", str(Path("outputs") / ".mplconfig"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from backend.intelligent_control.config import ControllerConfig, SafetyConfig
from backend.intelligent_control.curriculum import CurriculumManager
from backend.intelligent_control.logging_utils import save_csv_records, save_json_report
from backend.intelligent_control.mission_runner import MissionResult, MissionRunner
from backend.intelligent_control.route_loader import GlobalRoute, load_global_route
from backend.intelligent_control.td3_agent import TD3Agent


class ComparativeEvaluator:
    """Runs multi-trial controlled comparisons across navigation configurations."""

    CONFIG_MODES = (
        ("A_Baseline_No_TD3", "BASELINE"),
        ("B_TD3_Without_Fuzzy_Safety", "TD3_NO_SAFETY"),
        ("C_TD3_With_Fuzzy_Safety", "TD3_WITH_FUZZY_SAFETY"),
    )

    def __init__(
        self,
        controller_config: ControllerConfig,
        safety_config: SafetyConfig,
        td3_agent: TD3Agent,
    ) -> None:
        self.cfg = controller_config
        self.safety_cfg = safety_config
        self.td3_agent = td3_agent
        self.runner = MissionRunner(
            controller_config=controller_config,
            safety_config=safety_config,
            td3_agent=td3_agent,
        )

    def run_comparative_experiments(
        self,
        route: GlobalRoute | str | Path,
        seeds: Sequence[int] = (101, 102, 103, 104, 105),
        include_dynamic_obstacles: bool = True,
    ) -> Dict[str, Any]:
        """Run all 3 configurations across the specified random seeds and record actual metrics."""
        if isinstance(route, (str, Path)):
            global_route = load_global_route(route)
        else:
            global_route = route

        trial_rows: List[Dict[str, Any]] = []
        summary_rows: List[Dict[str, Any]] = []
        representative_trajectories: Dict[str, List[tuple[float, float, float]]] = {}

        for label, nav_mode in self.CONFIG_MODES:
            mode_results: List[MissionResult] = []
            for idx, seed in enumerate(seeds):
                res = self.runner.run_mission(
                    route=global_route,
                    nav_mode=nav_mode,
                    execution_backend="kinematic",
                    include_dynamic_obstacles=include_dynamic_obstacles,
                    seed=int(seed),
                    process_noise_std_mps=0.12,
                )
                mode_results.append(res)
                if idx == 0:
                    representative_trajectories[label] = res.trajectory_xyz

                row = {"config_label": label, "trial_seed": int(seed)}
                row.update(res.to_summary_dict())
                trial_rows.append(row)

            summary_rows.append(self._aggregate_mode_metrics(label, nav_mode, mode_results))

        log_dir = Path(self.cfg.paths.log_dir)
        out_dir = Path(self.cfg.paths.output_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        trials_csv = save_csv_records(log_dir / "evaluation_trials.csv", trial_rows)
        summary_csv = save_csv_records(log_dir / "evaluation_summary.csv", summary_rows)

        traj_plot = self._plot_trajectories(
            global_route=global_route,
            trajectories=representative_trajectories,
            include_dynamic=include_dynamic_obstacles,
            out_path=out_dir / "trajectory_comparison.png",
        )
        metrics_plot = self._plot_summary_bars(
            summary_rows=summary_rows,
            out_path=out_dir / "metrics_comparison.png",
        )

        report = {
            "evaluation_environment": "LIGHTWEIGHT_3D_KINEMATIC_SIMULATION (Not physical or AirSim flight)",
            "mission_id": global_route.mission_id,
            "planned_route_length_m": global_route.path_metrics.get("planned_path_length_m", 0.0),
            "num_seeds_per_config": len(seeds),
            "seeds": list(seeds),
            "configurations": summary_rows,
            "artifacts": {
                "trials_csv": str(trials_csv),
                "summary_csv": str(summary_csv),
                "trajectory_plot": str(traj_plot),
                "metrics_plot": str(metrics_plot),
            },
        }
        report_json = save_json_report(out_dir / "evaluation_report.json", report)
        report["artifacts"]["report_json"] = str(report_json)
        return report

    @staticmethod
    def _aggregate_mode_metrics(
        label: str, nav_mode: str, results: List[MissionResult]
    ) -> Dict[str, Any]:
        def _mean_std(vals: Sequence[float]) -> tuple[float, float]:
            arr = np.asarray(vals, dtype=np.float64)
            return round(float(np.mean(arr)), 4), round(float(np.std(arr)), 4)

        sr_m, sr_s = _mean_std([1.0 if r.success else 0.0 for r in results])
        cov_m, cov_s = _mean_std([r.monitoring_coverage_ratio for r in results])
        col_rate_m, col_rate_s = _mean_std([1.0 if r.has_collided else 0.0 for r in results])
        col_cnt_m, col_cnt_s = _mean_std([float(r.collision_count) for r in results])
        min_d_m, min_d_s = _mean_std([r.min_obstacle_distance_m for r in results])
        dist_m, dist_s = _mean_std([r.total_travelled_distance_m for r in results])
        smooth_m, smooth_s = _mean_std([r.control_smoothness_rms_jerk_mps2 for r in results])
        int_cnt_m, int_cnt_s = _mean_std([float(r.fuzzy_intervention_count) for r in results])
        int_rate_m, int_rate_s = _mean_std([r.fuzzy_intervention_rate for r in results])
        energy_m, energy_s = _mean_std([r.estimated_energy_proxy_joules for r in results])
        exec_t_m, exec_t_s = _mean_std([r.execution_time_sec for r in results])

        planned_len = results[0].planned_route_length_m if results else 0.0
        plan_time = results[0].planning_time_sec if results else 0.0

        return {
            "config_label": label,
            "nav_mode": nav_mode,
            "num_trials": len(results),
            "mission_completion_rate_mean": sr_m,
            "mission_completion_rate_std": sr_s,
            "waypoint_coverage_mean": cov_m,
            "waypoint_coverage_std": cov_s,
            "collision_rate_mean": col_rate_m,
            "collision_rate_std": col_rate_s,
            "collision_count_mean": col_cnt_m,
            "collision_count_std": col_cnt_s,
            "min_obstacle_distance_m_mean": min_d_m,
            "min_obstacle_distance_m_std": min_d_s,
            "planned_route_length_m": planned_len,
            "travelled_distance_m_mean": dist_m,
            "travelled_distance_m_std": dist_s,
            "path_length_ratio_flown_vs_planned": round(dist_m / max(planned_len, 1e-6), 4),
            "control_smoothness_rms_accel_mps2_mean": smooth_m,
            "control_smoothness_rms_accel_mps2_std": smooth_s,
            "fuzzy_interventions_count_mean": int_cnt_m,
            "fuzzy_interventions_count_std": int_cnt_s,
            "fuzzy_intervention_rate_mean": int_rate_m,
            "fuzzy_intervention_rate_std": int_rate_s,
            "estimated_energy_proxy_joules_mean": energy_m,
            "estimated_energy_proxy_joules_std": energy_s,
            "planning_time_sec": plan_time,
            "execution_time_sec_mean": exec_t_m,
            "execution_time_sec_std": exec_t_s,
        }

    @staticmethod
    def _plot_trajectories(
        global_route: GlobalRoute,
        trajectories: Dict[str, List[tuple[float, float, float]]],
        include_dynamic: bool,
        out_path: Path,
    ) -> Path:
        fig, ax = plt.subplots(figsize=(9, 6.5))

        # Planned route
        planned_pts = np.array(
            [[pt.x, pt.y] for pt in global_route.intermediate_path_points], dtype=np.float64
        )
        ax.plot(
            planned_pts[:, 0],
            planned_pts[:, 1],
            "k--",
            linewidth=1.6,
            label="Global Planned Route (GA+2-Opt)",
        )

        # Monitoring waypoints
        mon_pts = np.array([[w.x, w.y] for w in global_route.monitoring_waypoints], dtype=np.float64)
        ax.scatter(
            mon_pts[:, 0],
            mon_pts[:, 1],
            c="gold",
            edgecolors="black",
            s=95,
            zorder=5,
            label="Monitoring Waypoints",
        )

        # Obstacles
        obstacles = CurriculumManager.build_evaluation_route_obstacles(
            global_route.static_obstacles, include_dynamic=include_dynamic
        )
        for idx, obs in enumerate(obstacles):
            circle = plt.Circle(
                (obs.center_xyz[0], obs.center_xyz[1]),
                obs.radius,
                color="crimson" if "DYN" not in obs.id else "darkorange",
                alpha=0.38,
                label="Static Obstacle" if idx == 0 else ("Dynamic Hazard Zone" if "DYN" in obs.id and idx == len(global_route.static_obstacles) else None),
            )
            ax.add_patch(circle)

        colors = {
            "A_Baseline_No_TD3": "#d62728",
            "B_TD3_Without_Fuzzy_Safety": "#1f77b4",
            "C_TD3_With_Fuzzy_Safety": "#2ca02c",
        }
        for label, traj in trajectories.items():
            arr = np.asarray(traj, dtype=np.float64)
            if len(arr) > 0:
                ax.plot(
                    arr[:, 0],
                    arr[:, 1],
                    color=colors.get(label, "purple"),
                    linewidth=2.2,
                    label=label,
                )

        ax.scatter(
            [global_route.start_position.x],
            [global_route.start_position.y],
            c="limegreen",
            s=110,
            marker="^",
            edgecolors="black",
            zorder=6,
            label="Start",
        )
        ax.scatter(
            [global_route.destination.x],
            [global_route.destination.y],
            c="royalblue",
            s=120,
            marker="*",
            edgecolors="black",
            zorder=6,
            label="Destination",
        )

        ax.set_title("UAV Trajectory Comparison (Planner Frame X-East, Y-North)")
        ax.set_xlabel("X / East (metres)")
        ax.set_ylabel("Y / North (metres)")
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="best", fontsize=8.5)
        fig.tight_layout()
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        return out_path

    @staticmethod
    def _plot_summary_bars(summary_rows: List[Dict[str, Any]], out_path: Path) -> Path:
        labels = [r["config_label"].replace("_", "\n") for r in summary_rows]
        sr = [r["mission_completion_rate_mean"] * 100.0 for r in summary_rows]
        cr = [r["collision_rate_mean"] * 100.0 for r in summary_rows]
        min_d = [r["min_obstacle_distance_m_mean"] for r in summary_rows]
        energy = [r["estimated_energy_proxy_joules_mean"] for r in summary_rows]

        fig, axes = plt.subplots(2, 2, figsize=(10, 7))
        bar_colors = ["#d62728", "#1f77b4", "#2ca02c"]

        axes[0, 0].bar(labels, sr, color=bar_colors)
        axes[0, 0].set_title("Strict Mission Completion Rate (%)")
        axes[0, 0].set_ylim(0, 110)

        axes[0, 1].bar(labels, cr, color=bar_colors)
        axes[0, 1].set_title("Collision Rate (%)")
        axes[0, 1].set_ylim(0, 110)

        axes[1, 0].bar(labels, min_d, color=bar_colors)
        axes[1, 0].axhline(2.5, color="red", linestyle="--", linewidth=1.2, label="Critical (2.5m)")
        axes[1, 0].set_title("Minimum Observed Obstacle Distance (m)")
        axes[1, 0].legend(loc="best", fontsize=8)

        axes[1, 1].bar(labels, energy, color=bar_colors)
        axes[1, 1].set_title("Estimated Control-Effort Proxy (J-equiv)")

        for ax in axes.flat:
            ax.grid(True, axis="y", linestyle=":", alpha=0.6)

        fig.suptitle("Comparative Evaluation Metrics (Lightweight 3D Kinematic Env)", fontsize=12)
        fig.tight_layout()
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        return out_path
