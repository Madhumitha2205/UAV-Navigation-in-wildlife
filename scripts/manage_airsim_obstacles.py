#!/usr/bin/env python3
"""CLI Utility to Spawn, List, Validate, and Clean Up 3D Wildlife Obstacles in AirSim Blocks.

Usage from PowerShell in project root:
  # Spawn the complete 3D obstacle layout (canopy, mountain ridge, elephant herd region):
  .\.venv\Scripts\python.exe scripts/manage_airsim_obstacles.py --action spawn

  # Clean up ONLY project-created (wl_obs_*) obstacles:
  .\.venv\Scripts\python.exe scripts/manage_airsim_obstacles.py --action cleanup

  # List project-created obstacles currently in the AirSim scene:
  .\.venv\Scripts\python.exe scripts/manage_airsim_obstacles.py --action list

  # Run Phase 2 single-obstacle spawn/verify/delete test:
  .\.venv\Scripts\python.exe scripts/manage_airsim_obstacles.py --action test-single

  # Run full Phase 2-4 verification (single test + camera/LiDAR + collision + full layout spawn):
  .\.venv\Scripts\python.exe scripts/manage_airsim_obstacles.py --action verify-all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.intelligent_control.airsim_client import AirSimUAVClient
from backend.intelligent_control.config import load_controller_config
from backend.intelligent_control.obstacle_spawner import AirSimObstacleSpawner
from backend.intelligent_control.route_loader import load_global_route


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage and validate 3D wildlife obstacles in AirSim Blocks."
    )
    parser.add_argument(
        "--action",
        type=str,
        choices=["spawn", "cleanup", "list", "test-single", "verify-all"],
        required=True,
        help="Action to perform in the connected AirSim Blocks simulator.",
    )
    parser.add_argument(
        "--env-config",
        type=str,
        default="configs/default_environment.json",
        help="Path to planner environment configuration JSON.",
    )
    parser.add_argument(
        "--controller-config",
        type=str,
        default="configs/controller_config.json",
        help="Path to controller configuration JSON.",
    )
    parser.add_argument(
        "--route",
        type=str,
        default="outputs/controller_route.json",
        help="Path to validated controller route JSON for clearance verification.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ctrl_cfg = load_controller_config(args.controller_config)
    spawner = AirSimObstacleSpawner(
        controller_config=ctrl_cfg,
        planner_config_path=args.env_config,
    )

    uav_client = AirSimUAVClient(ctrl_cfg.airsim)
    uav_client.connect()
    raw_client = uav_client.raw_client

    route = load_global_route(args.route) if Path(args.route).exists() else None

    if args.action == "list":
        owned = spawner.list_project_obstacles(raw_client)
        payload = {
            "action": "list",
            "project_obstacle_count": len(owned),
            "project_obstacles": owned,
        }
        print(json.dumps(payload, indent=2))
        return 0

    if args.action == "cleanup":
        report = spawner.cleanup_project_obstacles(raw_client)
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.success else 1

    if args.action == "test-single":
        report = spawner.test_single_obstacle_lifecycle(raw_client)
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.success else 1

    if args.action == "spawn":
        report = spawner.spawn_full_layout(raw_client, route=route)
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.success else 1

    if args.action == "verify-all":
        single_rep = spawner.test_single_obstacle_lifecycle(raw_client)
        sensor_rep = spawner.verify_visual_and_lidar_detection(raw_client)
        collision_rep = spawner.verify_controlled_collision(raw_client)
        layout_rep = spawner.spawn_full_layout(raw_client, route=route)

        combined = {
            "phase2_single_obstacle_test": single_rep.to_dict(),
            "phase4_visual_and_lidar_verification": sensor_rep,
            "phase4_controlled_collision_verification": collision_rep,
            "phase3_full_layout_spawn": layout_rep.to_dict(),
        }
        out_file = Path("outputs/obstacle_validation_report.json")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(combined, indent=2), encoding="utf-8")
        print(json.dumps(combined, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
