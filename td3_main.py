"""Main Entry Point for TD3 Local UAV Navigation, Adaptive Fuzzy Safety, and AirSim Integration.

Supported explicit modes (`--mode`):
- `baseline`         : Run baseline route-following controller in the kinematic simulator (no TD3 checkpoint required).
- `airsim-baseline`  : Connect to a live AirSim multirotor server and execute the validated route using baseline controller.
- `train`            : Train the TD3 agent in the lightweight 3D kinematic environment (no AirSim required).
- `dry-run`          : Validate route JSON, coordinate transforms, and TD3+Fuzzy controller execution locally.
- `evaluate`         : Run multi-seed comparative evaluation (Config A: Baseline, Config B: TD3, Config C: TD3+Fuzzy)
                       and generate CSV logs and Matplotlib summary plots.
- `airsim`           : Connect to a live AirSim multirotor server and execute a saved, trained TD3 policy with Fuzzy Safety.
                       Never runs silently—requires explicit `--mode airsim` and a trained checkpoint.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path("outputs") / ".mplconfig"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from backend.intelligent_control.config import load_controller_config, load_safety_config
from backend.intelligent_control.curriculum import run_curriculum_training
from backend.intelligent_control.evaluation import ComparativeEvaluator
from backend.intelligent_control.logging_utils import save_csv_records, save_json_report, setup_logger
from backend.intelligent_control.mission_runner import MissionResult, MissionRunner
from backend.intelligent_control.route_loader import GlobalRoute, load_global_route
from backend.intelligent_control.td3_agent import TD3Agent


def _save_mission_artifacts(
    route: GlobalRoute,
    mission_res: MissionResult,
    summary_json_path: Path,
    trajectory_csv_path: Path,
    trajectory_plot_path: Path,
    title: str,
) -> dict[str, str]:
    """Save mission summary JSON, trajectory CSV, and 2D trajectory plot."""
    summary = mission_res.to_summary_dict()
    traj_records = [
        {"step": idx, "x": round(pt[0], 4), "y": round(pt[1], 4), "z": round(pt[2], 4)}
        for idx, pt in enumerate(mission_res.trajectory_xyz)
    ]
    save_csv_records(trajectory_csv_path, traj_records)

    # Plot 2D trajectory vs planned route
    fig, ax = plt.subplots(figsize=(9, 8), dpi=150)
    planned_pts = np.array([[pt.x, pt.y] for pt in route.intermediate_path_points], dtype=np.float64)
    ax.plot(planned_pts[:, 0], planned_pts[:, 1], "k--", linewidth=1.6, label="Planned Global Route")

    if mission_res.trajectory_xyz:
        flown = np.asarray(mission_res.trajectory_xyz, dtype=np.float64)
        ax.plot(flown[:, 0], flown[:, 1], color="#1f77b4", linewidth=2.4, label=f"Flown Trajectory ({mission_res.nav_mode})")
        ax.scatter([flown[-1, 0]], [flown[-1, 1]], c="magenta", s=90, marker="X", zorder=7, label="Final Position")

    mon_pts = np.array([[w.x, w.y] for w in route.monitoring_waypoints], dtype=np.float64)
    if len(mon_pts) > 0:
        ax.scatter(mon_pts[:, 0], mon_pts[:, 1], c="gold", edgecolors="black", s=100, zorder=5, label="Monitoring Waypoints")
        for order_idx, wp in enumerate(route.monitoring_waypoints, 1):
            ax.text(wp.x, wp.y + 1.5, f"#{order_idx} {wp.waypoint_id}", fontsize=8, ha="center", fontweight="bold")

    for idx, obs in enumerate(route.static_obstacles):
        circle = plt.Circle(
            (obs.x, obs.y),
            obs.radius,
            color="crimson",
            alpha=0.3,
            label="Obstacle" if idx == 0 else None,
        )
        ax.add_patch(circle)

    ax.scatter([route.start_position.x], [route.start_position.y], c="limegreen", s=120, marker="s", edgecolors="black", zorder=6, label="Start")
    ax.scatter([route.destination.x], [route.destination.y], c="royalblue", s=140, marker="*", edgecolors="black", zorder=6, label="Destination")

    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xlabel("X / East (metres)")
    ax.set_ylabel("Y / North (metres)")
    ax.set_aspect("equal")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="best", fontsize=8.5)
    trajectory_plot_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    import io

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    try:
        trajectory_plot_path.write_bytes(buf.getvalue())
    except OSError:
        if trajectory_plot_path.exists():
            trajectory_plot_path.unlink()
        trajectory_plot_path.write_bytes(buf.getvalue())

    artifacts = {
        "summary_json": str(summary_json_path),
        "trajectory_csv": str(trajectory_csv_path),
        "trajectory_plot": str(trajectory_plot_path),
    }
    summary["artifacts"] = artifacts
    save_json_report(summary_json_path, summary)
    return artifacts


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Intelligent Hierarchical UAV Navigation - Part 2: Baseline, TD3 Local Control, Fuzzy Safety & AirSim"
    )
    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["baseline", "airsim-baseline", "train", "dry-run", "evaluate", "airsim"],
        help="Execution mode: baseline | airsim-baseline | train | dry-run | evaluate | airsim",
    )
    parser.add_argument(
        "--controller-config",
        type=str,
        default="configs/controller_config.json",
        help="Path to controller_config.json",
    )
    parser.add_argument(
        "--safety-config",
        type=str,
        default="configs/safety_config.json",
        help="Path to safety_config.json",
    )
    parser.add_argument(
        "--route",
        type=str,
        default=None,
        help="Override path to global route JSON file",
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default=None,
        help="Override path to TD3 model checkpoint (.pt)",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=None,
        help="Number of training episodes for --mode train",
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=[101, 102, 103, 104, 105],
        help="Random seeds for --mode evaluate",
    )
    parser.add_argument(
        "--spawn-obstacles",
        action="store_true",
        help="Spawn and verify 3D wildlife obstacles in AirSim Blocks before executing an AirSim mission.",
    )
    parser.add_argument(
        "--cleanup-obstacles",
        action="store_true",
        help="Clean up project-spawned 3D obstacles in AirSim Blocks after mission completion.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ctrl_cfg = load_controller_config(args.controller_config)
    safety_cfg = load_safety_config(args.safety_config)

    log_dir = Path(ctrl_cfg.paths.log_dir)
    logger = setup_logger("main", log_file=log_dir / "execution.log")

    route_path = args.route or ctrl_cfg.paths.route_input_path
    ckpt_path = Path(args.checkpoint or ctrl_cfg.paths.default_checkpoint)

    if args.mode == "train":
        logger.info("Starting TD3 curriculum training in lightweight 3D kinematic environment...")
        res = run_curriculum_training(
            controller_config=ctrl_cfg,
            safety_config=safety_cfg,
            total_episodes=args.episodes,
            save_path=ckpt_path,
        )
        logger.info("Training complete. Summary: %s", json.dumps(res["summary"]))
        print(json.dumps(res["summary"], indent=2))
        return 0

    # Load and validate global route for baseline, airsim-baseline, dry-run, evaluate, or airsim modes
    route = load_global_route(route_path)
    logger.info(
        "Loaded validated global route '%s' from '%s' with %d monitoring waypoints and %d path points.",
        route.mission_id,
        route_path,
        len(route.monitoring_waypoints),
        len(route.intermediate_path_points),
    )

    out_dir = Path(ctrl_cfg.paths.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "baseline":
        logger.info("Running kinematic BASELINE route-following mission (no TD3 checkpoint required)...")
        runner = MissionRunner(ctrl_cfg, safety_cfg, td3_agent=None)
        mission_res = runner.run_mission(
            route=route,
            nav_mode="BASELINE",
            execution_backend="kinematic",
            include_dynamic_obstacles=False,
            seed=ctrl_cfg.td3.seed,
            process_noise_std_mps=0.0,
        )
        artifacts = _save_mission_artifacts(
            route=route,
            mission_res=mission_res,
            summary_json_path=out_dir / "baseline_kinematic_result.json",
            trajectory_csv_path=out_dir / "baseline_kinematic_trajectory.csv",
            trajectory_plot_path=out_dir / "baseline_kinematic_trajectory.png",
            title="Kinematic Baseline Route-Following Trajectory (Planner Frame)",
        )
        save_json_report(log_dir / "baseline_kinematic_result.json", mission_res.to_summary_dict())
        logger.info(
            "Kinematic baseline finished: success=%s, reason=%s, coverage=%d/%d, final_dist=%.2fm",
            mission_res.success,
            mission_res.termination_reason,
            mission_res.monitoring_waypoints_reached,
            mission_res.monitoring_waypoints_total,
            mission_res.final_distance_to_destination_m,
        )
        summary = mission_res.to_summary_dict()
        summary["artifacts"] = artifacts
        print(json.dumps(summary, indent=2))
        return 0 if mission_res.success else 2

    if args.mode == "airsim-baseline":
        logger.info(
            "Explicit AirSim BASELINE route-following mode requested. Connecting to %s:%d...",
            ctrl_cfg.airsim.ip,
            ctrl_cfg.airsim.port,
        )
        obs_spawn_report = None
        if args.spawn_obstacles:
            from backend.intelligent_control.airsim_client import AirSimUAVClient
            from backend.intelligent_control.obstacle_spawner import AirSimObstacleSpawner

            spawner = AirSimObstacleSpawner(controller_config=ctrl_cfg)
            tmp_client = AirSimUAVClient(ctrl_cfg.airsim)
            tmp_client.connect()
            obs_spawn_report = spawner.spawn_full_layout(tmp_client.raw_client, route=route)
            logger.info(
                "Spawned %d 3D wildlife obstacles in AirSim Blocks (min route clearance=%.2fm).",
                len(obs_spawn_report.spawned_objects),
                obs_spawn_report.min_route_clearance_m or 0.0,
            )

        runner = MissionRunner(ctrl_cfg, safety_cfg, td3_agent=None)
        try:
            mission_res = runner.run_mission(
                route=route,
                nav_mode="BASELINE",
                execution_backend="airsim",
                include_dynamic_obstacles=False,
            )
        finally:
            if args.cleanup_obstacles:
                from backend.intelligent_control.airsim_client import AirSimUAVClient
                from backend.intelligent_control.obstacle_spawner import AirSimObstacleSpawner

                spawner = AirSimObstacleSpawner(controller_config=ctrl_cfg)
                tmp_client = AirSimUAVClient(ctrl_cfg.airsim)
                tmp_client.connect()
                spawner.cleanup_project_obstacles(tmp_client.raw_client)

        artifacts = _save_mission_artifacts(
            route=route,
            mission_res=mission_res,
            summary_json_path=out_dir / "airsim_baseline_result.json",
            trajectory_csv_path=out_dir / "airsim_baseline_trajectory.csv",
            trajectory_plot_path=out_dir / "airsim_baseline_trajectory.png",
            title="AirSim 3D Blocks Baseline Flight Trajectory (Planner Frame)",
        )
        summary = mission_res.to_summary_dict()
        summary["artifacts"] = artifacts
        if obs_spawn_report is not None:
            summary["spawned_obstacles_count"] = len(obs_spawn_report.spawned_objects)
            summary["min_route_clearance_to_3d_obstacles_m"] = obs_spawn_report.min_route_clearance_m
        save_json_report(log_dir / "airsim_baseline_result.json", summary)
        logger.info(
            "AirSim baseline finished: success=%s, reason=%s, coverage=%d/%d, final_dist=%.2fm",
            mission_res.success,
            mission_res.termination_reason,
            mission_res.monitoring_waypoints_reached,
            mission_res.monitoring_waypoints_total,
            mission_res.final_distance_to_destination_m,
        )
        print(json.dumps(summary, indent=2))
        return 0 if mission_res.success else 2

    agent = TD3Agent(td3_config=ctrl_cfg.td3, limits_config=ctrl_cfg.vehicle_limits)
    if not ckpt_path.exists():
        msg = (
            f"[ERROR] Trained TD3 checkpoint not found at '{ckpt_path}'.\n"
            "To train the TD3 model checkpoint first, run:\n"
            "  .\\.venv\\Scripts\\python.exe td3_main.py --mode train --episodes 150\n"
            "Or to run the route-following controller without TD3, use:\n"
            "  .\\.venv\\Scripts\\python.exe td3_main.py --mode baseline\n"
            "  .\\.venv\\Scripts\\python.exe td3_main.py --mode airsim-baseline"
        )
        logger.error(msg)
        print(msg, file=sys.stderr)
        return 1
    agent.load_checkpoint(ckpt_path)
    agent.set_eval_mode(True)
    if not agent.is_trained:
        raise RuntimeError(f"Checkpoint '{ckpt_path}' is marked as untrained. Refusing policy execution.")

    if args.mode == "dry-run":
        logger.info("Running simulation-free dry-run validation of route and TD3+Fuzzy controller...")
        runner = MissionRunner(ctrl_cfg, safety_cfg, td3_agent=agent)
        mission_res = runner.run_mission(
            route=route,
            nav_mode="TD3_WITH_FUZZY_SAFETY",
            execution_backend="kinematic",
            include_dynamic_obstacles=True,
            seed=ctrl_cfg.td3.seed,
            process_noise_std_mps=0.0,
        )
        artifacts = _save_mission_artifacts(
            route=route,
            mission_res=mission_res,
            summary_json_path=out_dir / "td3_dry_run_result.json",
            trajectory_csv_path=out_dir / "td3_dry_run_trajectory.csv",
            trajectory_plot_path=out_dir / "td3_dry_run_trajectory.png",
            title="TD3 + Adaptive Fuzzy Safety Kinematic Trajectory",
        )
        summary = mission_res.to_summary_dict()
        summary["artifacts"] = artifacts
        save_json_report(log_dir / "dry_run_result.json", summary)
        if mission_res.intervention_logs:
            save_csv_records(log_dir / "dry_run_fuzzy_interventions.csv", mission_res.intervention_logs)
        logger.info("Dry-run completed: success=%s, reason=%s", mission_res.success, mission_res.termination_reason)
        print(json.dumps(summary, indent=2))
        return 0 if mission_res.success else 2

    if args.mode == "evaluate":
        logger.info("Running comparative evaluation across Configurations A, B, and C...")
        evaluator = ComparativeEvaluator(ctrl_cfg, safety_cfg, td3_agent=agent)
        report = evaluator.run_comparative_experiments(route=route, seeds=args.seeds)
        logger.info("Evaluation completed. Artifacts saved to %s", json.dumps(report["artifacts"]))
        print(json.dumps(report, indent=2))
        return 0

    if args.mode == "airsim":
        logger.info(
            "Explicit AirSim TD3+Fuzzy execution mode requested. Connecting to %s:%d...",
            ctrl_cfg.airsim.ip,
            ctrl_cfg.airsim.port,
        )
        runner = MissionRunner(ctrl_cfg, safety_cfg, td3_agent=agent)
        mission_res = runner.run_mission(
            route=route,
            nav_mode="TD3_WITH_FUZZY_SAFETY",
            execution_backend="airsim",
            include_dynamic_obstacles=True,
        )
        artifacts = _save_mission_artifacts(
            route=route,
            mission_res=mission_res,
            summary_json_path=out_dir / "airsim_td3_mission_result.json",
            trajectory_csv_path=out_dir / "airsim_td3_trajectory.csv",
            trajectory_plot_path=out_dir / "airsim_td3_trajectory.png",
            title="AirSim 3D Blocks TD3 + Fuzzy Safety Flight Trajectory",
        )
        summary = mission_res.to_summary_dict()
        summary["artifacts"] = artifacts
        save_json_report(log_dir / "airsim_mission_result.json", summary)
        if mission_res.intervention_logs:
            save_csv_records(log_dir / "airsim_fuzzy_interventions.csv", mission_res.intervention_logs)
        print(json.dumps(summary, indent=2))
        return 0 if mission_res.success else 2

    return 1


if __name__ == "__main__":
    sys.exit(main())
