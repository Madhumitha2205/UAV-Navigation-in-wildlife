#!/usr/bin/env python3
"""End-to-End Orchestration Pipeline for UAV Navigation in Wildlife Monitoring.

Executes the complete mission workflow using the existing project architecture:
  Stage 1: Generate global route (GA + 2-Opt + A*)
  Stage 2: Independently validate route geometry, continuity, and obstacle clearance
  Stage 3: Export both planned_route.json and controller_route.json
  Stage 4: Run kinematic baseline simulation and verify 100% waypoint & destination completion
  Stage 5: Optionally execute the validated route in 3D AirSim Blocks (only if requested and AirSim is reachable)

Usage from PowerShell in project root:
  # Run planner + validation + kinematic baseline verification:
  .\.venv\Scripts\python.exe run_pipeline.py

  # Run full pipeline including 3D AirSim Blocks execution (with Blocks.exe open):
  .\.venv\Scripts\python.exe run_pipeline.py --airsim

  # Run full pipeline using trained TD3 + Fuzzy Safety in AirSim Blocks:
  .\.venv\Scripts\python.exe run_pipeline.py --airsim --controller td3
"""

from __future__ import annotations

import argparse
import json
import logging
import socket
import sys
from pathlib import Path

from backend.global_planner.config import PlannerConfig
from backend.global_planner.planner_service import GlobalPlannerService
from backend.intelligent_control.config import load_controller_config, load_safety_config
from backend.intelligent_control.logging_utils import save_json_report, setup_logger
from backend.intelligent_control.mission_runner import MissionRunner
from backend.intelligent_control.route_loader import load_global_route
from backend.intelligent_control.td3_agent import TD3Agent
from td3_main import _save_mission_artifacts


def _is_airsim_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="End-to-End Wildlife UAV Global Planning, Kinematic Verification, and 3D AirSim Pipeline"
    )
    parser.add_argument(
        "--env-config",
        type=str,
        default="configs/default_environment.json",
        help="Path to global planner environment configuration JSON.",
    )
    parser.add_argument(
        "--controller-config",
        type=str,
        default="configs/controller_config.json",
        help="Path to controller configuration JSON.",
    )
    parser.add_argument(
        "--safety-config",
        type=str,
        default="configs/safety_config.json",
        help="Path to fuzzy safety configuration JSON.",
    )
    parser.add_argument(
        "--controller",
        type=str,
        choices=["baseline", "td3"],
        default="baseline",
        help="Controller mode: 'baseline' (no training required) or 'td3' (requires trained checkpoint + fuzzy safety).",
    )
    parser.add_argument(
        "--airsim",
        action="store_true",
        help="After kinematic verification succeeds, execute the validated route in 3D AirSim Blocks.",
    )
    parser.add_argument(
        "--spawn-obstacles",
        action="store_true",
        help="Spawn and verify 3D wildlife obstacles in AirSim Blocks before executing the AirSim flight.",
    )
    parser.add_argument(
        "--cleanup-obstacles",
        action="store_true",
        help="Clean up project-spawned 3D obstacles in AirSim Blocks after the AirSim flight completes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ctrl_cfg = load_controller_config(args.controller_config)
    safety_cfg = load_safety_config(args.safety_config)
    out_dir = Path(ctrl_cfg.paths.output_dir)
    log_dir = Path(ctrl_cfg.paths.log_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logger("pipeline", log_file=log_dir / "pipeline_execution.log")

    # -------------------------------------------------------------------------
    # Stage 1, 2 & 3: Global Route Generation, Validation, and Export
    # -------------------------------------------------------------------------
    logger.info("=== STAGE 1-3: Global Route Planning, Validation & Export ===")
    planner_cfg = PlannerConfig.from_json_file(args.env_config)
    planner_cfg.output_directory = str(out_dir)
    planner_service = GlobalPlannerService(planner_cfg)
    env = planner_service.generate_environment(planner_cfg.environment)
    planned_route = planner_service.plan_route(env, planner_cfg)

    planned_json_path = out_dir / "planned_route.json"
    controller_json_path = out_dir / "controller_route.json"
    planner_service.export_route(planned_route, planned_json_path)
    planner_service.export_controller_route(planned_route, controller_json_path, environment=env)

    if planned_route.status != "success" or not planned_route.validation.is_valid:
        logger.error(
            "Global route failed validation (status=%s, errors=%s). Refusing to proceed to mission execution.",
            planned_route.status,
            planned_route.validation.errors,
        )
        return 1

    logger.info(
        "Validated route exported: length=%.2fm, waypoints=%d/%d, path_points=%d, min_clearance=%.2fm",
        planned_route.metrics.path_length,
        planned_route.metrics.visited_waypoints,
        planned_route.metrics.required_waypoints,
        len(planned_route.path_points),
        planned_route.metrics.minimum_obstacle_clearance,
    )

    # Load controller route via authoritative route_loader
    route = load_global_route(controller_json_path)

    # Prepare TD3 agent if requested
    nav_mode = "BASELINE"
    agent = None
    if args.controller == "td3":
        nav_mode = "TD3_WITH_FUZZY_SAFETY"
        ckpt_path = Path(ctrl_cfg.paths.default_checkpoint)
        if not ckpt_path.exists():
            msg = (
                f"[ERROR] Trained TD3 checkpoint not found at '{ckpt_path}'.\n"
                "Please train the TD3 model first:\n"
                "  .\\.venv\\Scripts\\python.exe td3_main.py --mode train --episodes 150\n"
                "Or run in baseline mode (default):\n"
                "  .\\.venv\\Scripts\\python.exe run_pipeline.py"
            )
            logger.error(msg)
            print(msg, file=sys.stderr)
            return 1
        agent = TD3Agent(td3_config=ctrl_cfg.td3, limits_config=ctrl_cfg.vehicle_limits)
        agent.load_checkpoint(ckpt_path)
        agent.set_eval_mode(True)

    # -------------------------------------------------------------------------
    # Stage 4 & 5: Kinematic Simulation & Verification
    # -------------------------------------------------------------------------
    logger.info("=== STAGE 4-5: Kinematic Simulation Verification (%s) ===", nav_mode)
    runner = MissionRunner(ctrl_cfg, safety_cfg, td3_agent=agent)
    kin_res = runner.run_mission(
        route=route,
        nav_mode=nav_mode,
        execution_backend="kinematic",
        include_dynamic_obstacles=(nav_mode != "BASELINE"),
        seed=ctrl_cfg.td3.seed,
        process_noise_std_mps=0.0,
    )
    kin_prefix = "baseline_kinematic" if nav_mode == "BASELINE" else "td3_dry_run"
    kin_artifacts = _save_mission_artifacts(
        route=route,
        mission_res=kin_res,
        summary_json_path=out_dir / f"{kin_prefix}_result.json",
        trajectory_csv_path=out_dir / f"{kin_prefix}_trajectory.csv",
        trajectory_plot_path=out_dir / f"{kin_prefix}_trajectory.png",
        title=f"Kinematic {nav_mode} Route-Following Trajectory (Planner Frame)",
    )

    if not kin_res.success:
        logger.error(
            "Kinematic verification did not succeed (reason=%s, coverage=%d/%d). Stopping before AirSim execution.",
            kin_res.termination_reason,
            kin_res.monitoring_waypoints_reached,
            kin_res.monitoring_waypoints_total,
        )
        print(json.dumps(kin_res.to_summary_dict(), indent=2))
        return 2

    logger.info(
        "Kinematic verification PASSED: %d/%d waypoints, destination reached (dist=%.2fm), 0 collisions.",
        kin_res.monitoring_waypoints_reached,
        kin_res.monitoring_waypoints_total,
        kin_res.final_distance_to_destination_m,
    )

    # -------------------------------------------------------------------------
    # Stage 6 & 7: Optional 3D AirSim Blocks Execution
    # -------------------------------------------------------------------------
    if not args.airsim:
        summary = {
            "pipeline_stage": "kinematic_verified",
            "planned_route": str(planned_json_path),
            "controller_route": str(controller_json_path),
            "kinematic_mission": kin_res.to_summary_dict(),
            "kinematic_artifacts": kin_artifacts,
            "next_step_airsim_command": (
                f".\\.venv\\Scripts\\python.exe run_pipeline.py --airsim --controller {args.controller}"
            ),
        }
        print(json.dumps(summary, indent=2))
        return 0

    logger.info("=== STAGE 6-7: 3D AirSim Blocks Execution (%s) ===", nav_mode)
    if not _is_airsim_reachable(ctrl_cfg.airsim.ip, ctrl_cfg.airsim.port):
        msg = (
            f"[ERROR] AirSim simulator is not reachable at {ctrl_cfg.airsim.ip}:{ctrl_cfg.airsim.port}.\n"
            "Start AirSim Blocks first:\n"
            '  Start-Process "D:\\AirSimEnvironments\\Blocks\\Blocks\\WindowsNoEditor\\Blocks\\Binaries\\Win64\\Blocks.exe" '
            '-ArgumentList "-ResX=1280","-ResY=720","-windowed"\n'
            "Then re-run this command."
        )
        logger.error(msg)
        print(msg, file=sys.stderr)
        return 3

    if args.spawn_obstacles:
        from backend.intelligent_control.airsim_client import AirSimUAVClient
        from backend.intelligent_control.obstacle_spawner import AirSimObstacleSpawner

        spawner = AirSimObstacleSpawner(controller_config=ctrl_cfg, planner_config_path=args.env_config)
        tmp_client = AirSimUAVClient(ctrl_cfg.airsim)
        tmp_client.connect()
        obs_rep = spawner.spawn_full_layout(tmp_client.raw_client, environment=env, route=route)
        logger.info(
            "Spawned %d 3D wildlife obstacles in AirSim Blocks (min route clearance=%.2fm).",
            len(obs_rep.spawned_objects),
            obs_rep.min_route_clearance_m or 0.0,
        )

    try:
        airsim_res = runner.run_mission(
            route=route,
            nav_mode=nav_mode,
            execution_backend="airsim",
            include_dynamic_obstacles=(nav_mode != "BASELINE"),
        )
    finally:
        if args.cleanup_obstacles:
            from backend.intelligent_control.airsim_client import AirSimUAVClient
            from backend.intelligent_control.obstacle_spawner import AirSimObstacleSpawner

            spawner = AirSimObstacleSpawner(controller_config=ctrl_cfg, planner_config_path=args.env_config)
            tmp_client = AirSimUAVClient(ctrl_cfg.airsim)
            tmp_client.connect()
            spawner.cleanup_project_obstacles(tmp_client.raw_client)
    airsim_prefix = "airsim_baseline" if nav_mode == "BASELINE" else "airsim_td3"
    airsim_artifacts = _save_mission_artifacts(
        route=route,
        mission_res=airsim_res,
        summary_json_path=out_dir / f"{airsim_prefix}_result.json",
        trajectory_csv_path=out_dir / f"{airsim_prefix}_trajectory.csv",
        trajectory_plot_path=out_dir / f"{airsim_prefix}_trajectory.png",
        title=f"AirSim 3D Blocks {nav_mode} Flight Trajectory (Planner Frame)",
    )
    save_json_report(log_dir / f"{airsim_prefix}_result.json", airsim_res.to_summary_dict())

    full_summary = {
        "pipeline_stage": "airsim_completed",
        "planned_route": str(planned_json_path),
        "controller_route": str(controller_json_path),
        "kinematic_mission": kin_res.to_summary_dict(),
        "airsim_mission": airsim_res.to_summary_dict(),
        "airsim_artifacts": airsim_artifacts,
    }
    print(json.dumps(full_summary, indent=2))
    return 0 if airsim_res.success else 2


if __name__ == "__main__":
    sys.exit(main())
