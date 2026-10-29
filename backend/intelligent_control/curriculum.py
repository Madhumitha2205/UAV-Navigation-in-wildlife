"""Curriculum Learning and Dynamic Obstacle Scenario Generator for TD3 UAV Navigation.

Defines 5 configurable difficulty stages:
- Stage 1: Clear corridor (no obstacles) - learns direct 3D waypoint tracking.
- Stage 2: Sparse static obstacles - learns basic local obstacle avoidance.
- Stage 3: Dense static obstacles - learns multi-obstacle corridor navigation.
- Stage 4: Scripted moving obstacles - learns dynamic wildlife/hazard avoidance.
- Stage 5: Complex multi-waypoint corridor with both static and moving obstacles.

Note on Research Integrity:
This curriculum is a structured progressive training schedule and is NOT claimed to be
mathematically optimal without dedicated ablation experiments.
Dynamic obstacles are repeatable scripted geometric spheres representing moving hazards
or wildlife movement corridors; they do not use computer-vision wildlife detection.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from backend.intelligent_control.config import ControllerConfig, SafetyConfig
from backend.intelligent_control.fuzzy_safety import AdaptiveFuzzySafetyLayer
from backend.intelligent_control.logging_utils import save_csv_records, save_json_report
from backend.intelligent_control.replay_buffer import ReplayBuffer
from backend.intelligent_control.rl_environment import DynamicObstacle, LightweightUAVEnv
from backend.intelligent_control.td3_agent import TD3Agent


@dataclass
class ScenarioSpec:
    stage_id: int
    name: str
    start_pos: Tuple[float, float, float]
    waypoints: List[Tuple[float, float, float]]
    obstacles: List[DynamicObstacle]
    description: str = ""


class CurriculumManager:
    """Manages progressive training stages and repeatable obstacle scenarios."""

    STAGE_NAMES = {
        1: "Stage1_Clear_Target",
        2: "Stage2_Sparse_Static_Obstacles",
        3: "Stage3_Complex_Static_Obstacles",
        4: "Stage4_Scripted_Dynamic_Obstacles",
        5: "Stage5_Integrated_MultiWaypoint_Dynamic",
    }

    def __init__(
        self,
        controller_config: Optional[ControllerConfig] = None,
        safety_config: Optional[SafetyConfig] = None,
        seed: int = 42,
    ) -> None:
        self.cfg = controller_config or ControllerConfig()
        self.safety_cfg = safety_config or SafetyConfig()
        self.rng = np.random.default_rng(seed)
        self.current_stage: int = 1
        self.stage_history: List[Dict[str, Any]] = []

    def generate_stage_scenario(self, stage_id: int, episode_idx: int = 0) -> ScenarioSpec:
        """Generate a reproducible 360-degree scenario for the requested curriculum stage (1..5)."""
        ep_rng = np.random.default_rng(self.cfg.td3.seed + stage_id * 1000 + episode_idx)
        start = (0.0, 0.0, 15.0)

        # Full 360-degree target randomization across short and medium leg lengths
        angle = float(ep_rng.uniform(-np.pi, np.pi))
        dist = float(ep_rng.uniform(10.0, 22.0))
        tx = dist * np.cos(angle)
        ty = dist * np.sin(angle)
        tz = float(ep_rng.uniform(14.0, 18.0))
        dir_x, dir_y = np.cos(angle), np.sin(angle)
        perp_x, perp_y = -dir_y, dir_x

        if stage_id == 1:
            return ScenarioSpec(
                stage_id=1,
                name=self.STAGE_NAMES[1],
                start_pos=start,
                waypoints=[(tx, ty, tz)],
                obstacles=[],
                description="Obstacle-free waypoint tracking.",
            )

        if stage_id == 2:
            # Place 1 static obstacle near the direct line of sight
            mid_x, mid_y, mid_z = 0.5 * tx, 0.5 * ty, 0.5 * (15.0 + tz)
            lateral_offset = float(ep_rng.uniform(-1.0, 1.0))
            obs = [
                DynamicObstacle(
                    id="S2_STATIC_1",
                    center_xyz=np.array([mid_x + lateral_offset * perp_x, mid_y + lateral_offset * perp_y, mid_z]),
                    radius=1.6,
                )
            ]
            return ScenarioSpec(
                stage_id=2,
                name=self.STAGE_NAMES[2],
                start_pos=start,
                waypoints=[(tx, ty, tz)],
                obstacles=obs,
                description="Single static obstacle near the flight path.",
            )

        if stage_id == 3:
            # Staggered static obstacle gate along the leg direction
            obs = [
                DynamicObstacle(
                    id="S3_STATIC_1",
                    center_xyz=np.array([0.35 * tx + 0.8 * perp_x, 0.35 * ty + 0.8 * perp_y, 15.5]),
                    radius=1.6,
                ),
                DynamicObstacle(
                    id="S3_STATIC_2",
                    center_xyz=np.array([0.68 * tx - 0.8 * perp_x, 0.68 * ty - 0.8 * perp_y, tz]),
                    radius=1.6,
                ),
            ]
            return ScenarioSpec(
                stage_id=3,
                name=self.STAGE_NAMES[3],
                start_pos=start,
                waypoints=[(tx, ty, tz)],
                obstacles=obs,
                description="Multi-obstacle static layout.",
            )

        if stage_id == 4:
            # Scripted oscillating / moving obstacle crossing the corridor
            obs = [
                DynamicObstacle(
                    id="S4_DYN_1",
                    center_xyz=np.array([0.50 * tx, 0.50 * ty, 15.5]),
                    radius=1.6,
                    oscillation_amplitude_xyz=np.array([2.5 * perp_x, 2.5 * perp_y, 0.0]),
                    oscillation_freq_hz=0.15,
                ),
            ]
            return ScenarioSpec(
                stage_id=4,
                name=self.STAGE_NAMES[4],
                start_pos=start,
                waypoints=[(tx, ty, tz)],
                obstacles=obs,
                description="Scripted moving obstacle crossing corridor.",
            )

        # Stage 5: Two-segment mission with static + dynamic obstacles
        wp1 = (0.50 * tx, 0.50 * ty, 16.0)
        wp2 = (tx, ty, tz)
        obs = [
            DynamicObstacle(
                id="S5_STATIC_1",
                center_xyz=np.array([0.25 * tx + 0.5 * perp_x, 0.25 * ty + 0.5 * perp_y, 15.5]),
                radius=1.5,
            ),
            DynamicObstacle(
                id="S5_DYN_2",
                center_xyz=np.array([0.75 * tx, 0.75 * ty, 16.0]),
                radius=1.5,
                oscillation_amplitude_xyz=np.array([2.2 * perp_x, 2.2 * perp_y, 0.4]),
                oscillation_freq_hz=0.15,
            ),
        ]
        return ScenarioSpec(
            stage_id=5,
            name=self.STAGE_NAMES[5],
            start_pos=start,
            waypoints=[wp1, wp2],
            obstacles=obs,
            description="Multi-waypoint corridor with static and scripted dynamic obstacles.",
        )

    @staticmethod
    def build_evaluation_route_obstacles(
        route_static_obstacles: Sequence[Any],
        include_dynamic: bool = True,
    ) -> List[DynamicObstacle]:
        """Build repeatable static + scripted dynamic obstacles for full route evaluation."""
        obs_list: List[DynamicObstacle] = []
        for s_obs in route_static_obstacles:
            obs_list.append(
                DynamicObstacle(
                    id=str(s_obs.id),
                    center_xyz=np.array([float(s_obs.x), float(s_obs.y), float(s_obs.z)], dtype=np.float64),
                    radius=float(s_obs.radius),
                )
            )
        if include_dynamic:
            # Add two repeatable scripted dynamic obstacles along the wildlife monitoring route
            obs_list.append(
                DynamicObstacle(
                    id="DYN_HAZARD_FLOCK_1",
                    center_xyz=np.array([26.0, 13.5, 16.5], dtype=np.float64),
                    radius=1.8,
                    oscillation_amplitude_xyz=np.array([0.0, 3.2, 0.0], dtype=np.float64),
                    oscillation_freq_hz=0.12,
                )
            )
            obs_list.append(
                DynamicObstacle(
                    id="DYN_HAZARD_WIND_GUST_2",
                    center_xyz=np.array([50.0, 40.0, 15.8], dtype=np.float64),
                    radius=1.8,
                    oscillation_amplitude_xyz=np.array([2.5, -2.5, 0.0], dtype=np.float64),
                    oscillation_freq_hz=0.10,
                )
            )
        return obs_list


def _compute_teacher_guidance_action(
    env: LightweightUAVEnv,
    safety_layer: AdaptiveFuzzySafetyLayer,
) -> np.ndarray:
    """Compute a smooth potential-field teacher velocity for warmup & residual exploration."""
    rel = env.current_target - env.uav_pos
    dist = float(np.linalg.norm(rel))
    if dist > 1e-6:
        dir_vec = rel / dist
    else:
        dir_vec = np.zeros(3, dtype=np.float64)

    desired_speed = min(env.limits.max_velocity_xy_mps * 0.85, max(1.2, 0.6 * dist))
    desired_vel = dir_vec * desired_speed
    desired_vel[2] = np.clip(desired_vel[2], -env.limits.max_velocity_z_mps, env.limits.max_velocity_z_mps)

    if env.last_obstacle_obs is not None:
        filtered = safety_layer.filter_action(desired_vel, env.uav_vel, env.last_obstacle_obs)
        return np.asarray(filtered.final_action, dtype=np.float32)
    return desired_vel.astype(np.float32)


def run_curriculum_training(
    controller_config: ControllerConfig,
    safety_config: SafetyConfig,
    total_episodes: Optional[int] = None,
    resume_checkpoint: Optional[str | Path] = None,
    save_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Train the TD3 agent across the 5-stage curriculum in the lightweight environment."""
    start_wall = time.perf_counter()
    env = LightweightUAVEnv(
        controller_config=controller_config,
        safe_distance_m=safety_config.safe_distance_m,
        seed=controller_config.td3.seed,
    )
    agent = TD3Agent(
        td3_config=controller_config.td3,
        limits_config=controller_config.vehicle_limits,
    )
    safety_layer = AdaptiveFuzzySafetyLayer(
        safety_config=safety_config,
        limits_config=controller_config.vehicle_limits,
    )
    replay_buffer = ReplayBuffer(
        state_dim=controller_config.td3.state_dim,
        action_dim=controller_config.td3.action_dim,
        max_size=controller_config.td3.replay_buffer_size,
        seed=controller_config.td3.seed,
    )
    curriculum = CurriculumManager(
        controller_config=controller_config,
        safety_config=safety_config,
        seed=controller_config.td3.seed,
    )

    if resume_checkpoint is not None and Path(resume_checkpoint).exists():
        agent.load_checkpoint(resume_checkpoint)

    num_episodes = int(
        total_episodes
        if total_episodes is not None
        else controller_config.curriculum.episodes_per_stage * 5
    )

    episode_logs: List[Dict[str, Any]] = []
    stage_success_window: List[int] = []
    stage_episodes_count = 0
    total_steps = 0

    for ep in range(1, num_episodes + 1):
        ep_t0 = time.perf_counter()
        scenario = curriculum.generate_stage_scenario(curriculum.current_stage, episode_idx=ep)
        state = env.reset(
            start_pos=scenario.start_pos,
            waypoints=scenario.waypoints,
            obstacles=scenario.obstacles,
            seed=controller_config.td3.seed + ep,
        )

        ep_reward = 0.0
        ep_steps = 0
        ep_collisions = 0
        ep_completed = False
        critic_losses: List[float] = []

        # Progressive exploration schedule: blend guided exploration during warmup, then pure TD3 + noise
        guidance_prob = max(0.0, 1.0 - (ep / max(1.0, num_episodes * 0.55)))

        while True:
            total_steps += 1
            ep_steps += 1

            if total_steps <= controller_config.td3.warmup_steps or (
                env.rng.random() < guidance_prob
            ):
                base_action = _compute_teacher_guidance_action(env, safety_layer)
                noise = env.rng.normal(0.0, 0.10, size=3).astype(np.float32) * agent.max_action_np
                action = np.clip(base_action + noise, env.action_low, env.action_high)
            else:
                noise_scale = max(0.05, controller_config.td3.exploration_noise * (1.0 - 0.5 * (ep / num_episodes)))
                action = agent.select_action(state, add_noise=True, noise_scale=noise_scale)

            next_state, reward, done, info = env.step(action)
            replay_buffer.add(state, action, next_state, reward, done)
            state = next_state
            ep_reward += reward

            if len(replay_buffer) >= controller_config.td3.batch_size:
                loss_info = agent.train_step(replay_buffer)
                if loss_info["updated"] > 0:
                    critic_losses.append(loss_info["critic_loss"])

            if info["has_collided"]:
                ep_collisions += 1
            if info["completed_mission"]:
                ep_completed = True

            if done:
                break

        agent.trained_episodes += 1
        stage_episodes_count += 1
        stage_success_window.append(1 if (ep_completed and ep_collisions == 0) else 0)
        if len(stage_success_window) > 15:
            stage_success_window.pop(0)

        recent_sr = float(np.mean(stage_success_window)) if stage_success_window else 0.0
        ep_dur = time.perf_counter() - ep_t0

        episode_logs.append(
            {
                "episode": ep,
                "stage": curriculum.current_stage,
                "stage_name": scenario.name,
                "episode_reward": round(float(ep_reward), 4),
                "success": int(ep_completed and ep_collisions == 0),
                "collision": int(ep_collisions > 0),
                "episode_length": ep_steps,
                "recent_success_rate": round(recent_sr, 4),
                "mean_critic_loss": round(float(np.mean(critic_losses)) if critic_losses else 0.0, 5),
                "duration_sec": round(ep_dur, 4),
            }
        )

        # Promote curriculum stage if success threshold met or stage episode quota reached
        min_ep = controller_config.curriculum.min_episodes_before_promotion
        max_stage_ep = controller_config.curriculum.episodes_per_stage
        if curriculum.current_stage < 5:
            if (
                stage_episodes_count >= min_ep
                and recent_sr >= controller_config.curriculum.promotion_success_rate
            ) or (stage_episodes_count >= max_stage_ep):
                curriculum.current_stage += 1
                stage_episodes_count = 0
                stage_success_window.clear()

    total_wall = time.perf_counter() - start_wall
    ckpt_target = Path(save_path if save_path is not None else controller_config.paths.default_checkpoint)

    overall_sr = float(np.mean([r["success"] for r in episode_logs])) if episode_logs else 0.0
    final_20_sr = float(np.mean([r["success"] for r in episode_logs[-20:]])) if episode_logs else 0.0
    overall_cr = float(np.mean([r["collision"] for r in episode_logs])) if episode_logs else 0.0

    summary_meta = {
        "total_episodes": num_episodes,
        "total_steps": total_steps,
        "final_curriculum_stage": curriculum.current_stage,
        "overall_success_rate": round(overall_sr, 4),
        "final_20_episodes_success_rate": round(final_20_sr, 4),
        "overall_collision_rate": round(overall_cr, 4),
        "training_wall_time_sec": round(total_wall, 3),
    }
    agent.save_checkpoint(ckpt_target, extra_metadata=summary_meta)

    log_dir = Path(controller_config.paths.log_dir)
    csv_path = save_csv_records(log_dir / "td3_curriculum_training_log.csv", episode_logs)
    json_path = save_json_report(log_dir / "td3_training_summary.json", summary_meta)

    return {
        "checkpoint_path": str(ckpt_target),
        "training_csv_path": str(csv_path),
        "summary_json_path": str(json_path),
        "summary": summary_meta,
        "episode_logs": episode_logs,
    }
