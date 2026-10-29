"""Main Entry Point for TD3 Local UAV Navigation, Adaptive Fuzzy Safety, and AirSim Integration.

Supported explicit modes (`--mode`):
- `train`    : Train the TD3 agent in the lightweight 3D kinematic environment (no AirSim required).
- `dry-run`  : Validate route JSON, coordinate transforms, and controller execution locally without moving AirSim.
- `evaluate` : Run multi-seed comparative evaluation (Config A: Baseline, Config B: TD3, Config C: TD3+Fuzzy)
               and generate CSV logs and Matplotlib summary plots.
- `airsim`   : Connect to a live AirSim multirotor server and execute a saved, trained TD3 policy with Fuzzy Safety.
               Never runs silently—requires explicit `--mode airsim` and a trained checkpoint.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backend.intelligent_control.config import load_controller_config, load_safety_config
from backend.intelligent_control.curriculum import run_curriculum_training
from backend.intelligent_control.evaluation import ComparativeEvaluator
from backend.intelligent_control.logging_utils import save_csv_records, save_json_report, setup_logger
from backend.intelligent_control.mission_runner import MissionRunner
from backend.intelligent_control.route_loader import load_global_route
from backend.intelligent_control.td3_agent import TD3Agent


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Intelligent Hierarchical UAV Navigation - Part 2: TD3 Local Control, Fuzzy Safety & AirSim"
    )
    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["train", "dry-run", "evaluate", "airsim"],
        help="Execution mode: train | dry-run | evaluate | airsim",
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

    # Load and validate global route for dry-run, evaluate, or airsim modes
    route = load_global_route(route_path)
    logger.info(
        "Loaded validated global route '%s' with %d monitoring waypoints and %d path points.",
        route.mission_id,
        len(route.monitoring_waypoints),
        len(route.intermediate_path_points),
    )

    agent = TD3Agent(td3_config=ctrl_cfg.td3, limits_config=ctrl_cfg.vehicle_limits)
    if not ckpt_path.exists():
        raise FileNotFoundError(
            f"Trained TD3 checkpoint not found at '{ckpt_path}'. Run `--mode train` first."
        )
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
        summary = mission_res.to_summary_dict()
        save_json_report(log_dir / "dry_run_result.json", summary)
        if mission_res.intervention_logs:
            save_csv_records(log_dir / "dry_run_fuzzy_interventions.csv", mission_res.intervention_logs)
        logger.info("Dry-run completed: success=%s, reason=%s", mission_res.success, mission_res.termination_reason)
        print(json.dumps(summary, indent=2))
        return 0

    if args.mode == "evaluate":
        logger.info("Running comparative evaluation across Configurations A, B, and C...")
        evaluator = ComparativeEvaluator(ctrl_cfg, safety_cfg, td3_agent=agent)
        report = evaluator.run_comparative_experiments(route=route, seeds=args.seeds)
        logger.info("Evaluation completed. Artifacts saved to %s", json.dumps(report["artifacts"]))
        print(json.dumps(report, indent=2))
        return 0

    if args.mode == "airsim":
        logger.info(
            "Explicit AirSim execution mode requested. Connecting to %s:%d...",
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
        summary = mission_res.to_summary_dict()
        save_json_report(log_dir / "airsim_mission_result.json", summary)
        print(json.dumps(summary, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
