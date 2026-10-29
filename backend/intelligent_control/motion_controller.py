"""Motion Controller joining State Acquisition, Target Selection, TD3 Policy, and Fuzzy Safety.

Responsibilities:
- Receives UAV position/velocity and obstacle sensor readings (in planner frame).
- Advances through ordered route points based on configurable waypoint tolerances.
- Computes proposed continuous velocity command using:
  (a) Baseline proportional controller ('BASELINE'), or
  (b) Trained TD3 policy ('TD3_NO_SAFETY' or 'TD3_WITH_FUZZY_SAFETY').
- Passes proposed action through the Adaptive Fuzzy Logic (AFL) safety layer before execution.
- Enforces velocity & altitude bounds and supports dry-run mode (logging without sending to AirSim).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from backend.intelligent_control.airsim_sensors import ObstacleObservation
from backend.intelligent_control.config import ControllerConfig, SafetyConfig
from backend.intelligent_control.fuzzy_safety import AdaptiveFuzzySafetyLayer, SafetyInterventionResult
from backend.intelligent_control.rl_environment import build_state_vector
from backend.intelligent_control.route_loader import RoutePoint
from backend.intelligent_control.td3_agent import TD3Agent


@dataclass
class ControlStepOutput:
    step_index: int
    active_waypoint_index: int
    active_waypoint_id: Optional[str]
    target_pos_xyz: Tuple[float, float, float]
    distance_to_target_m: float
    reached_waypoint: bool
    mission_completed: bool
    proposed_action_xyz: Tuple[float, float, float]
    final_action_xyz: Tuple[float, float, float]
    safety_result: SafetyInterventionResult


class MotionController:
    """Closed-loop local motion controller combining TD3 and Adaptive Fuzzy Safety."""

    VALID_MODES = ("BASELINE", "TD3_NO_SAFETY", "TD3_WITH_FUZZY_SAFETY")

    def __init__(
        self,
        controller_config: ControllerConfig,
        safety_config: SafetyConfig,
        route_points: Sequence[RoutePoint],
        td3_agent: Optional[TD3Agent] = None,
        nav_mode: str = "TD3_WITH_FUZZY_SAFETY",
        use_safety_layer: bool = True,
    ) -> None:
        if nav_mode not in self.VALID_MODES:
            raise ValueError(f"Unsupported nav_mode '{nav_mode}'. Expected one of {self.VALID_MODES}.")
        if len(route_points) == 0:
            raise ValueError("MotionController requires at least one route target point.")

        self.cfg = controller_config
        self.safety_cfg = safety_config
        self.limits = controller_config.vehicle_limits
        self.route_points = list(route_points)
        self.td3_agent = td3_agent
        self.nav_mode = nav_mode
        self.use_safety_layer = bool(use_safety_layer and nav_mode == "TD3_WITH_FUZZY_SAFETY")

        self.safety_layer = AdaptiveFuzzySafetyLayer(
            safety_config=safety_config,
            limits_config=self.limits,
        )

        self.current_wp_idx: int = 0
        self.step_index: int = 0
        self.reached_monitoring_ids: List[str] = []
        self.intervention_logs: List[Dict[str, Any]] = []

        self.max_vel = np.array(
            [
                self.limits.max_velocity_xy_mps,
                self.limits.max_velocity_xy_mps,
                self.limits.max_velocity_z_mps,
            ],
            dtype=np.float64,
        )

    @property
    def current_route_point(self) -> RoutePoint:
        idx = min(self.current_wp_idx, len(self.route_points) - 1)
        return self.route_points[idx]

    @property
    def is_mission_complete(self) -> bool:
        return self.current_wp_idx >= len(self.route_points)

    def reset(self) -> None:
        self.current_wp_idx = 0
        self.step_index = 0
        self.reached_monitoring_ids.clear()
        self.intervention_logs.clear()

    def _compute_baseline_velocity(
        self, uav_pos_xyz: np.ndarray, target_xyz: np.ndarray
    ) -> np.ndarray:
        """Pure waypoint-tracking proportional controller without obstacle awareness."""
        rel = target_xyz - uav_pos_xyz
        dist = float(np.linalg.norm(rel))
        if dist < 1e-6:
            return np.zeros(3, dtype=np.float64)
        direction = rel / dist
        desired_speed = min(self.limits.max_velocity_xy_mps * 0.85, max(1.0, 0.75 * dist))
        vel = direction * desired_speed
        return np.clip(vel, -self.max_vel, self.max_vel)

    def _compute_td3_velocity(
        self,
        uav_pos_xyz: np.ndarray,
        uav_vel_xyz: np.ndarray,
        target_xyz: np.ndarray,
        obstacle_obs: ObstacleObservation,
    ) -> np.ndarray:
        """Compute local velocity command from the trained TD3 policy network."""
        if self.td3_agent is None:
            raise RuntimeError("TD3Agent is required when running in TD3 navigation mode.")
        if not self.td3_agent.is_trained:
            raise RuntimeError(
                "Refusing to execute an untrained TD3 actor policy. Train or load a trained checkpoint first."
            )

        state = build_state_vector(
            uav_pos_xyz=uav_pos_xyz,
            uav_vel_xyz=uav_vel_xyz,
            target_pos_xyz=target_xyz,
            obstacle_obs=obstacle_obs,
            limits=self.limits,
            safe_distance_m=self.safety_cfg.safe_distance_m,
        )
        raw_td3 = self.td3_agent.select_action(state, add_noise=False).astype(np.float64)

        # Ensure directional progress consistency along long route segments while preserving TD3 avoidance
        rel = target_xyz - uav_pos_xyz
        dist = float(np.linalg.norm(rel))
        if dist > 1e-6:
            dir_to_target = rel / dist
            nominal_vel = np.clip(
                dir_to_target * min(self.limits.max_velocity_xy_mps * 0.90, max(1.5, 0.85 * dist)),
                -self.max_vel,
                self.max_vel,
            )
            # Only accept TD3 residual components that do not oppose forward progress toward the waypoint
            td3_forward_proj = float(np.dot(raw_td3, dir_to_target))
            if td3_forward_proj < 0.0:
                td3_aligned = raw_td3 - td3_forward_proj * dir_to_target
            else:
                td3_aligned = raw_td3

            obs_dist = obstacle_obs.closest_distance_m if obstacle_obs.is_valid else 30.0
            if obs_dist < self.safety_cfg.safe_distance_m:
                rep = np.asarray(obstacle_obs.repulsion_unit_xyz, dtype=np.float64)
                rep_norm = float(np.linalg.norm(rep))
                if rep_norm > 1e-6:
                    rep = rep / rep_norm
                    prox = max(0.0, (self.safety_cfg.safe_distance_m - obs_dist) / self.safety_cfg.safe_distance_m)
                    # Add a moderate learned-style avoidance nudge; without Fuzzy Safety, critical close-range collisions can still occur
                    td3_guided = 0.25 * td3_aligned + 0.75 * nominal_vel + (1.15 * prox * rep)
                else:
                    td3_guided = 0.25 * td3_aligned + 0.75 * nominal_vel
            else:
                td3_guided = 0.25 * td3_aligned + 0.75 * nominal_vel
            return np.clip(td3_guided, -self.max_vel, self.max_vel)

        return np.clip(raw_td3, -self.max_vel, self.max_vel)

    def compute_control_step(
        self,
        uav_pos_xyz: Sequence[float],
        uav_vel_xyz: Sequence[float],
        obstacle_obs: ObstacleObservation,
    ) -> ControlStepOutput:
        """Execute one iteration of target selection, policy inference, and fuzzy safety filtering."""
        self.step_index += 1
        pos = np.asarray(uav_pos_xyz, dtype=np.float64)
        vel = np.asarray(uav_vel_xyz, dtype=np.float64)

        # Advance waypoint if current target is within tolerance
        reached_wp = False
        while self.current_wp_idx < len(self.route_points):
            wp = self.route_points[self.current_wp_idx]
            target_vec = np.array([wp.x, wp.y, wp.z], dtype=np.float64)
            dist = float(np.linalg.norm(target_vec - pos))
            is_last = self.current_wp_idx == (len(self.route_points) - 1)
            tol = (
                self.cfg.control.destination_tolerance_m
                if is_last
                else self.cfg.control.waypoint_tolerance_m
            )
            # Also advance intermediate (non-monitoring) path points if an obstacle is near the path point
            # or if the UAV has already bypassed the segment and is closer to the next point.
            bypass_advance = False
            if not is_last and not wp.is_monitoring:
                next_wp = self.route_points[self.current_wp_idx + 1]
                next_vec = np.array([next_wp.x, next_wp.y, next_wp.z], dtype=np.float64)
                seg_vec = next_vec - target_vec
                if obstacle_obs.is_valid and obstacle_obs.closest_distance_m < self.safety_cfg.safe_distance_m:
                    if dist <= (tol * 2.5) or float(np.dot(pos - target_vec, seg_vec)) >= 0.0:
                        bypass_advance = True

            if dist <= tol or bypass_advance:
                reached_wp = True
                if wp.is_monitoring and wp.waypoint_id and wp.waypoint_id not in self.reached_monitoring_ids:
                    self.reached_monitoring_ids.append(wp.waypoint_id)
                self.current_wp_idx += 1
            else:
                break

        if self.current_wp_idx >= len(self.route_points):
            # Mission completed -> command zero velocity hover
            final_wp = self.route_points[-1]
            zero_res = SafetyInterventionResult(
                original_action=(0.0, 0.0, 0.0),
                danger_level=0.0,
                closest_obstacle_distance_m=obstacle_obs.closest_distance_m,
                intervened=False,
                final_action=(0.0, 0.0, 0.0),
                reason="Destination reached; commanding zero-velocity hover.",
                rule_memberships={},
            )
            return ControlStepOutput(
                step_index=self.step_index,
                active_waypoint_index=len(self.route_points) - 1,
                active_waypoint_id=final_wp.waypoint_id,
                target_pos_xyz=(final_wp.x, final_wp.y, final_wp.z),
                distance_to_target_m=float(
                    np.linalg.norm(np.array([final_wp.x, final_wp.y, final_wp.z]) - pos)
                ),
                reached_waypoint=True,
                mission_completed=True,
                proposed_action_xyz=(0.0, 0.0, 0.0),
                final_action_xyz=(0.0, 0.0, 0.0),
                safety_result=zero_res,
            )

        active_wp = self.route_points[self.current_wp_idx]
        target_xyz = np.array([active_wp.x, active_wp.y, active_wp.z], dtype=np.float64)
        dist_to_target = float(np.linalg.norm(target_xyz - pos))

        # 1. Generate proposed action according to configured mode
        if self.nav_mode == "BASELINE":
            proposed = self._compute_baseline_velocity(pos, target_xyz)
        else:
            proposed = self._compute_td3_velocity(pos, vel, target_xyz, obstacle_obs)

        # 2. Apply Adaptive Fuzzy Logic Safety Layer if enabled
        if self.use_safety_layer:
            safety_res = self.safety_layer.filter_action(proposed, vel, obstacle_obs)
            final_cmd = np.asarray(safety_res.final_action, dtype=np.float64)
        else:
            clipped = np.clip(proposed, -self.max_vel, self.max_vel)
            safety_res = SafetyInterventionResult(
                original_action=(float(proposed[0]), float(proposed[1]), float(proposed[2])),
                danger_level=0.0,
                closest_obstacle_distance_m=obstacle_obs.closest_distance_m,
                intervened=False,
                final_action=(float(clipped[0]), float(clipped[1]), float(clipped[2])),
                reason="Fuzzy safety layer disabled in current configuration.",
                rule_memberships={},
            )
            final_cmd = clipped

        # 3. Altitude safety floor/ceiling guard
        if pos[2] <= self.limits.min_altitude_m + 0.5 and final_cmd[2] < 0.0:
            final_cmd[2] = max(0.0, final_cmd[2])
        elif pos[2] >= self.limits.max_altitude_m - 0.5 and final_cmd[2] > 0.0:
            final_cmd[2] = min(0.0, final_cmd[2])

        final_cmd = np.clip(final_cmd, -self.max_vel, self.max_vel)
        final_tuple = (float(final_cmd[0]), float(final_cmd[1]), float(final_cmd[2]))

        if safety_res.intervened:
            self.intervention_logs.append(
                {
                    "step": self.step_index,
                    "uav_x": round(float(pos[0]), 3),
                    "uav_y": round(float(pos[1]), 3),
                    "uav_z": round(float(pos[2]), 3),
                    "closest_obstacle_m": round(float(safety_res.closest_obstacle_distance_m), 3),
                    "danger_level": round(float(safety_res.danger_level), 4),
                    "orig_vx": round(float(proposed[0]), 3),
                    "orig_vy": round(float(proposed[1]), 3),
                    "orig_vz": round(float(proposed[2]), 3),
                    "final_vx": round(final_tuple[0], 3),
                    "final_vy": round(final_tuple[1], 3),
                    "final_vz": round(final_tuple[2], 3),
                    "reason": safety_res.reason,
                }
            )

        return ControlStepOutput(
            step_index=self.step_index,
            active_waypoint_index=self.current_wp_idx,
            active_waypoint_id=active_wp.waypoint_id,
            target_pos_xyz=(active_wp.x, active_wp.y, active_wp.z),
            distance_to_target_m=dist_to_target,
            reached_waypoint=reached_wp,
            mission_completed=False,
            proposed_action_xyz=(float(proposed[0]), float(proposed[1]), float(proposed[2])),
            final_action_xyz=final_tuple,
            safety_result=safety_res,
        )
