"""Reward Function Module for TD3 Local UAV Navigation.

Reward Terms (all documented with sign and scale):
1. Progress reward (+): `progress_weight * (prev_dist_to_target - curr_dist_to_target)`
   Incentivizes moving directly toward the current active waypoint. Bounded to prevent
   teleportation artifacts, and cannot be exploited by oscillating (going backward yields
   an equal and opposite negative reward, plus step penalties).
2. Waypoint reached bonus (+): `waypoint_bonus` (+25.0) awarded once per unique ordered
   waypoint reached within tolerance.
3. Mission completion bonus (+): `completion_bonus` (+80.0) awarded upon reaching the final
   destination without collision.
4. Collision penalty (-): `collision_penalty` (-100.0) applied on collision with any obstacle
   or altitude violation, immediately terminating the episode.
5. Obstacle proximity penalty (-): `proximity_penalty_weight * ((threshold - d) / threshold)^2`
   when `d < proximity_threshold_m` (default 6.0 m). Smoothly penalizes encroaching into hazard zones.
6. Control effort penalty (-): `control_effort_weight * ||u||^2 / ||u_max||^2`
   Penalizes excessive velocity commands (energy efficiency incentive).
7. Jerk / acceleration smoothness penalty (-): `jerk_penalty_weight * ||u_t - u_{t-1}||^2 / ||u_max||^2`
   Penalizes abrupt direction or speed changes.
8. Step / time penalty (-): `step_penalty` (-0.1) per timestep + `stationary_penalty` (-0.5)
   when UAV speed falls below `stationary_speed_threshold_mps` (0.15 m/s) away from target,
   ensuring the agent cannot accumulate high reward by hovering stationary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence
import numpy as np

from backend.intelligent_control.config import RewardConfig


@dataclass
class RewardBreakdown:
    total_reward: float
    progress_term: float
    waypoint_term: float
    completion_term: float
    collision_term: float
    proximity_term: float
    control_effort_term: float
    smoothness_term: float
    step_and_stationary_term: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "total_reward": self.total_reward,
            "progress_term": self.progress_term,
            "waypoint_term": self.waypoint_term,
            "completion_term": self.completion_term,
            "collision_term": self.collision_term,
            "proximity_term": self.proximity_term,
            "control_effort_term": self.control_effort_term,
            "smoothness_term": self.smoothness_term,
            "step_and_stationary_term": self.step_and_stationary_term,
        }


class NavigationRewardFunction:
    """Computes structured step rewards for local UAV waypoint navigation and obstacle avoidance."""

    def __init__(self, config: RewardConfig | None = None, max_speed_mps: float = 5.0) -> None:
        self.config = config or RewardConfig()
        self.max_speed_mps = max(float(max_speed_mps), 1e-3)

    def compute(
        self,
        prev_distance_to_target_m: float,
        curr_distance_to_target_m: float,
        action_vel_xyz: Sequence[float],
        prev_action_vel_xyz: Sequence[float],
        closest_obstacle_dist_m: float,
        reached_waypoint: bool = False,
        completed_mission: bool = False,
        has_collided: bool = False,
    ) -> RewardBreakdown:
        """Compute total step reward and individual diagnostic components."""
        u = np.asarray(action_vel_xyz, dtype=np.float64)
        u_prev = np.asarray(prev_action_vel_xyz, dtype=np.float64)
        speed = float(np.linalg.norm(u))

        # 1. Progress toward current target
        delta_d = float(prev_distance_to_target_m) - float(curr_distance_to_target_m)
        progress_term = float(self.config.progress_weight * delta_d)

        # 2. Waypoint & 3. Mission completion bonuses
        waypoint_term = float(self.config.waypoint_bonus) if reached_waypoint else 0.0
        completion_term = float(self.config.completion_bonus) if completed_mission else 0.0

        # 4. Collision penalty
        collision_term = float(self.config.collision_penalty) if has_collided else 0.0

        # 5. Obstacle proximity penalty (quadratic inside proximity_threshold_m)
        thresh = float(self.config.proximity_threshold_m)
        if np.isfinite(closest_obstacle_dist_m) and closest_obstacle_dist_m < thresh:
            norm_pen = max(0.0, (thresh - float(closest_obstacle_dist_m)) / max(thresh, 1e-6))
            proximity_term = float(self.config.proximity_penalty_weight * (norm_pen ** 2))
        else:
            proximity_term = 0.0

        # 6. Control effort penalty (normalized squared speed)
        norm_effort = float(np.sum(u ** 2)) / (self.max_speed_mps ** 2)
        control_effort_term = float(self.config.control_effort_weight * norm_effort)

        # 7. Smoothness / jerk penalty (normalized squared velocity change)
        norm_jerk = float(np.sum((u - u_prev) ** 2)) / (self.max_speed_mps ** 2)
        smoothness_term = float(self.config.jerk_penalty_weight * norm_jerk)

        # 8. Step penalty + anti-stationary penalty
        step_term = float(self.config.step_penalty)
        if (
            not reached_waypoint
            and not completed_mission
            and speed < float(self.config.stationary_speed_threshold_mps)
        ):
            step_term += float(self.config.stationary_penalty)

        total = (
            progress_term
            + waypoint_term
            + completion_term
            + collision_term
            + proximity_term
            + control_effort_term
            + smoothness_term
            + step_term
        )

        return RewardBreakdown(
            total_reward=float(total),
            progress_term=progress_term,
            waypoint_term=waypoint_term,
            completion_term=completion_term,
            collision_term=collision_term,
            proximity_term=proximity_term,
            control_effort_term=control_effort_term,
            smoothness_term=smoothness_term,
            step_and_stationary_term=step_term,
        )
