"""Lightweight 3D Kinematic UAV Reinforcement Learning Environment.

Does NOT require AirSim or Unreal Engine to run.
Maintains conceptual and dimensional parity with the AirSim state and action interface:
- State dimension: 12 floats
  [0..2] Normalized relative target vector: (target_pos - uav_pos) / pos_scale (clipped to [-1, 1])
  [3..5] Normalized UAV velocity: (vx / max_v_xy, vy / max_v_xy, vz / max_v_z)
  [6]    Normalized distance to target: min(dist / pos_scale, 1.0)
  [7..9] Unit repulsion vector from closest obstacle: (rx, ry, rz)
  [10]   Normalized closest obstacle surface distance: min(obs_dist / max_sensor_range, 1.0)
  [11]   Sensor hazard indicator in [0.0, 1.0]: max(0.0, (safe_dist - obs_dist) / safe_dist)
- Action dimension: 3 floats
  Bounded continuous velocity command [vx, vy, vz] in planner frame (metres/sec).

Dynamics Difference vs. 3D AirSim:
- This lightweight environment models first-order inertial velocity tracking:
  `v_{t+1} = v_t + clip(v_cmd - v_t, -a_max * dt, +a_max * dt)`
  `p_{t+1} = p_t + 0.5 * (v_t + v_{t+1}) * dt`
- AirSim simulates full 6-DOF rigid-body multirotor aerodynamics, rotor thrust/torque mixing,
  attitude pitch/roll coupling, and air drag.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
import numpy as np

from backend.intelligent_control.airsim_sensors import AirSimSensorReader, ObstacleObservation
from backend.intelligent_control.config import ControllerConfig, RewardConfig, VehicleLimitsConfig
from backend.intelligent_control.reward_function import NavigationRewardFunction


@dataclass
class DynamicObstacle:
    """Spherical obstacle in planner coordinates with optional scripted velocity/oscillation."""
    id: str
    center_xyz: np.ndarray
    radius: float
    velocity_xyz: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    oscillation_amplitude_xyz: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    oscillation_freq_hz: float = 0.0
    initial_center_xyz: Optional[np.ndarray] = None

    def __post_init__(self) -> None:
        self.center_xyz = np.asarray(self.center_xyz, dtype=np.float64).copy()
        self.velocity_xyz = np.asarray(self.velocity_xyz, dtype=np.float64).copy()
        self.oscillation_amplitude_xyz = np.asarray(self.oscillation_amplitude_xyz, dtype=np.float64).copy()
        if self.initial_center_xyz is None:
            self.initial_center_xyz = self.center_xyz.copy()

    def reset(self) -> None:
        if self.initial_center_xyz is not None:
            self.center_xyz = self.initial_center_xyz.copy()

    def step(self, dt: float, elapsed_time_sec: float) -> None:
        if self.oscillation_freq_hz > 0.0 and self.initial_center_xyz is not None:
            omega = 2.0 * np.pi * self.oscillation_freq_hz
            offset = self.oscillation_amplitude_xyz * np.sin(omega * elapsed_time_sec)
            self.center_xyz = self.initial_center_xyz + offset + self.velocity_xyz * elapsed_time_sec
            inst_vel = self.velocity_xyz + self.oscillation_amplitude_xyz * omega * np.cos(omega * elapsed_time_sec)
            self._current_vel = inst_vel
        else:
            self.center_xyz = self.center_xyz + self.velocity_xyz * dt
            self._current_vel = self.velocity_xyz

    @property
    def current_velocity(self) -> np.ndarray:
        return getattr(self, "_current_vel", self.velocity_xyz)


def build_state_vector(
    uav_pos_xyz: Sequence[float],
    uav_vel_xyz: Sequence[float],
    target_pos_xyz: Sequence[float],
    obstacle_obs: ObstacleObservation,
    limits: VehicleLimitsConfig,
    safe_distance_m: float = 6.0,
    pos_scale_m: float = 50.0,
    max_sensor_range_m: float = 30.0,
) -> np.ndarray:
    """Construct the 12-element normalized state vector shared by RL training and AirSim control."""
    pos = np.asarray(uav_pos_xyz, dtype=np.float64)
    vel = np.asarray(uav_vel_xyz, dtype=np.float64)
    target = np.asarray(target_pos_xyz, dtype=np.float64)

    rel_target = target - pos
    dist_to_target = float(np.linalg.norm(rel_target))
    norm_rel_target = np.clip(rel_target / max(pos_scale_m, 1.0), -1.0, 1.0)

    max_vxy = max(limits.max_velocity_xy_mps, 1e-3)
    max_vz = max(limits.max_velocity_z_mps, 1e-3)
    norm_vel = np.clip(
        np.array([vel[0] / max_vxy, vel[1] / max_vxy, vel[2] / max_vz], dtype=np.float64),
        -1.0,
        1.0,
    )
    norm_dist_target = float(np.clip(dist_to_target / max(pos_scale_m, 1.0), 0.0, 1.0))

    if obstacle_obs.is_valid and np.isfinite(obstacle_obs.closest_distance_m):
        obs_dist = float(obstacle_obs.closest_distance_m)
        rep = np.asarray(obstacle_obs.repulsion_unit_xyz, dtype=np.float64)
        norm_obs_dist = float(np.clip(obs_dist / max(max_sensor_range_m, 1.0), 0.0, 1.0))
        hazard = float(np.clip((safe_distance_m - obs_dist) / max(safe_distance_m, 1e-3), 0.0, 1.0))
    else:
        rep = np.zeros(3, dtype=np.float64)
        norm_obs_dist = 1.0
        hazard = 0.5  # conservative caution indicator when sensor is invalid

    state = np.array(
        [
            norm_rel_target[0],
            norm_rel_target[1],
            norm_rel_target[2],
            norm_vel[0],
            norm_vel[1],
            norm_vel[2],
            norm_dist_target,
            rep[0],
            rep[1],
            rep[2],
            norm_obs_dist,
            hazard,
        ],
        dtype=np.float32,
    )
    return state


class LightweightUAVEnv:
    """Lightweight 3D kinematic UAV navigation environment for TD3 training and evaluation."""

    STATE_DIM = 12
    ACTION_DIM = 3

    def __init__(
        self,
        controller_config: Optional[ControllerConfig] = None,
        safe_distance_m: float = 6.0,
        uav_radius_m: float = 0.5,
        seed: int = 42,
    ) -> None:
        self.cfg = controller_config or ControllerConfig()
        self.limits = self.cfg.vehicle_limits
        self.safe_distance_m = float(safe_distance_m)
        self.uav_radius_m = float(uav_radius_m)
        self.dt = 1.0 / max(self.cfg.control.control_frequency_hz, 1.0)
        self.max_steps = int(self.cfg.curriculum.max_steps_per_episode)

        self.rng = np.random.default_rng(seed)
        self.sensor_reader = AirSimSensorReader(self.cfg.airsim, max_lidar_range_m=30.0)
        self.reward_fn = NavigationRewardFunction(
            self.cfg.reward,
            max_speed_mps=self.limits.max_velocity_xy_mps,
        )

        self.uav_pos = np.array([0.0, 0.0, 15.0], dtype=np.float64)
        self.uav_vel = np.zeros(3, dtype=np.float64)
        self.prev_action = np.zeros(3, dtype=np.float64)
        self.waypoints: List[np.ndarray] = [np.array([25.0, 20.0, 15.0], dtype=np.float64)]
        self.current_wp_idx: int = 0
        self.obstacles: List[DynamicObstacle] = []
        self.step_count: int = 0
        self.elapsed_time_sec: float = 0.0
        self.last_obstacle_obs: Optional[ObstacleObservation] = None

    @property
    def action_low(self) -> np.ndarray:
        return np.array(
            [
                -self.limits.max_velocity_xy_mps,
                -self.limits.max_velocity_xy_mps,
                -self.limits.max_velocity_z_mps,
            ],
            dtype=np.float32,
        )

    @property
    def action_high(self) -> np.ndarray:
        return np.array(
            [
                self.limits.max_velocity_xy_mps,
                self.limits.max_velocity_xy_mps,
                self.limits.max_velocity_z_mps,
            ],
            dtype=np.float32,
        )

    @property
    def current_target(self) -> np.ndarray:
        idx = min(self.current_wp_idx, len(self.waypoints) - 1)
        return self.waypoints[idx]

    def reset(
        self,
        start_pos: Optional[Sequence[float]] = None,
        waypoints: Optional[Sequence[Sequence[float]]] = None,
        obstacles: Optional[List[DynamicObstacle]] = None,
        seed: Optional[int] = None,
    ) -> np.ndarray:
        """Reset environment to reproducible initial conditions and return 12D state vector."""
        if seed is not None:
            self.rng = np.random.default_rng(seed)

        if start_pos is not None:
            self.uav_pos = np.asarray(start_pos, dtype=np.float64).copy()
        else:
            self.uav_pos = np.array([0.0, 0.0, 15.0], dtype=np.float64)

        self.uav_vel = np.zeros(3, dtype=np.float64)
        self.prev_action = np.zeros(3, dtype=np.float64)
        self.step_count = 0
        self.elapsed_time_sec = 0.0
        self.current_wp_idx = 0

        if waypoints is not None and len(waypoints) > 0:
            self.waypoints = [np.asarray(wp, dtype=np.float64).copy() for wp in waypoints]
        else:
            self.waypoints = [np.array([25.0, 20.0, 15.0], dtype=np.float64)]

        if obstacles is not None:
            self.obstacles = obstacles
            for obs in self.obstacles:
                obs.reset()
        else:
            self.obstacles = []

        self.last_obstacle_obs = self._observe_obstacles()
        return self._get_state()

    def step(self, action_vel_xyz: Sequence[float]) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """Execute one timestep with bounded continuous velocity command [vx, vy, vz]."""
        cmd = np.clip(
            np.asarray(action_vel_xyz, dtype=np.float64),
            self.action_low,
            self.action_high,
        )

        prev_dist = float(np.linalg.norm(self.current_target - self.uav_pos))

        # First-order inertial velocity tracking
        max_dv = self.limits.max_acceleration_mps2 * self.dt
        dv = np.clip(cmd - self.uav_vel, -max_dv, max_dv)
        next_vel = np.clip(self.uav_vel + dv, self.action_low, self.action_high)
        next_pos = self.uav_pos + 0.5 * (self.uav_vel + next_vel) * self.dt

        self.uav_pos = next_pos
        self.uav_vel = next_vel
        self.step_count += 1
        self.elapsed_time_sec += self.dt

        # Advance dynamic obstacles
        for obs in self.obstacles:
            obs.step(self.dt, self.elapsed_time_sec)

        # Observe obstacles and check collisions / altitude bounds
        obs_reading = self._observe_obstacles()
        self.last_obstacle_obs = obs_reading

        altitude_violation = bool(
            self.uav_pos[2] < self.limits.min_altitude_m
            or self.uav_pos[2] > self.limits.max_altitude_m
        )
        has_collided = bool(obs_reading.has_collided or altitude_violation)

        curr_dist = float(np.linalg.norm(self.current_target - self.uav_pos))
        is_final_wp = self.current_wp_idx == (len(self.waypoints) - 1)
        tol = (
            self.cfg.control.destination_tolerance_m
            if is_final_wp
            else self.cfg.control.waypoint_tolerance_m
        )

        reached_waypoint = False
        completed_mission = False
        if not has_collided and curr_dist <= tol:
            reached_waypoint = True
            if is_final_wp:
                completed_mission = True
            else:
                self.current_wp_idx += 1

        reward_breakdown = self.reward_fn.compute(
            prev_distance_to_target_m=prev_dist,
            curr_distance_to_target_m=curr_dist,
            action_vel_xyz=cmd,
            prev_action_vel_xyz=self.prev_action,
            closest_obstacle_dist_m=obs_reading.closest_distance_m,
            reached_waypoint=reached_waypoint,
            completed_mission=completed_mission,
            has_collided=has_collided,
        )
        self.prev_action = cmd.copy()

        timeout = self.step_count >= self.max_steps
        done = bool(has_collided or completed_mission or timeout)

        info: Dict[str, Any] = {
            "step": self.step_count,
            "uav_pos": self.uav_pos.copy(),
            "uav_vel": self.uav_vel.copy(),
            "target_pos": self.current_target.copy(),
            "waypoint_index": self.current_wp_idx,
            "distance_to_target_m": float(np.linalg.norm(self.current_target - self.uav_pos)),
            "closest_obstacle_dist_m": obs_reading.closest_distance_m,
            "has_collided": has_collided,
            "altitude_violation": altitude_violation,
            "reached_waypoint": reached_waypoint,
            "completed_mission": completed_mission,
            "timeout": timeout,
            "reward_breakdown": reward_breakdown.to_dict(),
            "obstacle_observation": obs_reading,
        }
        return self._get_state(), reward_breakdown.total_reward, done, info

    def _observe_obstacles(self) -> ObstacleObservation:
        spheres = [
            (float(o.center_xyz[0]), float(o.center_xyz[1]), float(o.center_xyz[2]), float(o.radius))
            for o in self.obstacles
        ]
        vels = [
            (
                float(o.current_velocity[0]),
                float(o.current_velocity[1]),
                float(o.current_velocity[2]),
            )
            for o in self.obstacles
        ]
        return self.sensor_reader.compute_observation_from_spheres(
            uav_pos_xyz=self.uav_pos,
            uav_vel_xyz=self.uav_vel,
            obstacles_xyz_r=spheres,
            obstacle_vels_xyz=vels,
            uav_radius_m=self.uav_radius_m,
            sensor_mode="LIGHTWEIGHT_KINEMATIC_SIM",
        )

    def _get_state(self) -> np.ndarray:
        obs = self.last_obstacle_obs or self._observe_obstacles()
        return build_state_vector(
            uav_pos_xyz=self.uav_pos,
            uav_vel_xyz=self.uav_vel,
            target_pos_xyz=self.current_target,
            obstacle_obs=obs,
            limits=self.limits,
            safe_distance_m=self.safe_distance_m,
        )
