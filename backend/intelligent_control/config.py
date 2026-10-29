"""Configuration management for TD3 Local Navigation, Fuzzy Safety, and AirSim Integration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AirSimConfig:
    ip: str = "127.0.0.1"
    port: int = 41451
    vehicle_name: str = "SimpleFlight"
    lidar_sensor_name: str = "LidarSensor1"
    timeout_sec: float = 10.0
    takeoff_altitude_m: float = 15.0
    default_velocity_mps: float = 3.0


@dataclass
class CoordinateMappingConfig:
    planner_frame: str = "ENU_ALT_UP"
    airsim_frame: str = "NED"
    x_to_north: float = 0.0
    y_to_north: float = 1.0
    x_to_east: float = 1.0
    y_to_east: float = 0.0
    z_sign: float = -1.0
    origin_ned: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    origin_planner: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: float = 1.0
    description: str = (
        "Planner X=East, Y=North, Z=Altitude(+Up) in metres -> AirSim North=Y, East=X, Down=-Z"
    )


@dataclass
class VehicleLimitsConfig:
    max_velocity_xy_mps: float = 5.0
    max_velocity_z_mps: float = 2.0
    max_acceleration_mps2: float = 4.0
    min_altitude_m: float = 2.0
    max_altitude_m: float = 80.0


@dataclass
class ControlLoopConfig:
    control_frequency_hz: float = 10.0
    command_duration_sec: float = 0.25
    waypoint_tolerance_m: float = 2.5
    destination_tolerance_m: float = 2.0
    max_mission_steps: int = 600
    max_mission_time_sec: float = 180.0


@dataclass
class TD3Config:
    state_dim: int = 12
    action_dim: int = 3
    hidden_dim: int = 128
    actor_lr: float = 3e-4
    critic_lr: float = 3e-4
    gamma: float = 0.99
    tau: float = 0.005
    policy_noise: float = 0.2
    noise_clip: float = 0.5
    policy_freq: int = 2
    exploration_noise: float = 0.15
    batch_size: int = 64
    replay_buffer_size: int = 25000
    warmup_steps: int = 256
    seed: int = 42


@dataclass
class RewardConfig:
    progress_weight: float = 3.0
    waypoint_bonus: float = 25.0
    completion_bonus: float = 80.0
    collision_penalty: float = -100.0
    proximity_penalty_weight: float = -4.0
    proximity_threshold_m: float = 6.0
    control_effort_weight: float = -0.05
    jerk_penalty_weight: float = -0.08
    step_penalty: float = -0.1
    stationary_penalty: float = -0.5
    stationary_speed_threshold_mps: float = 0.15


@dataclass
class CurriculumConfig:
    episodes_per_stage: int = 30
    promotion_success_rate: float = 0.7
    min_episodes_before_promotion: int = 15
    max_steps_per_episode: int = 200


@dataclass
class PathsConfig:
    route_input_path: str = "configs/sample_global_route.json"
    checkpoint_dir: str = "models"
    default_checkpoint: str = "models/td3_wildlife_uav.pt"
    log_dir: str = "logs"
    output_dir: str = "outputs"


@dataclass
class FuzzyMembershipConfig:
    distance_critical_peak_m: float = 2.5
    distance_near_center_m: float = 4.25
    distance_safe_start_m: float = 6.0
    closing_slow_max_mps: float = 0.5
    closing_moderate_center_mps: float = 2.0
    closing_fast_min_mps: float = 3.5


@dataclass
class SafetyConfig:
    safe_distance_m: float = 6.0
    critical_distance_m: float = 2.5
    collision_radius_m: float = 1.0
    max_repulsion_speed_mps: float = 3.5
    braking_gain: float = 0.85
    vertical_clearance_boost_mps: float = 0.6
    closing_speed_scale_mps: float = 5.0
    sensor_invalid_fallback_speed_scale: float = 0.5
    membership: FuzzyMembershipConfig = field(default_factory=FuzzyMembershipConfig)
    intervention_threshold: float = 0.15
    emergency_brake_threshold: float = 0.8

    def validate(self) -> None:
        if self.critical_distance_m <= 0.0:
            raise ValueError("critical_distance_m must be positive.")
        if self.safe_distance_m <= self.critical_distance_m:
            raise ValueError("safe_distance_m must be strictly greater than critical_distance_m.")
        if not (0.0 <= self.intervention_threshold <= 1.0):
            raise ValueError("intervention_threshold must be in [0, 1].")


@dataclass
class ControllerConfig:
    airsim: AirSimConfig = field(default_factory=AirSimConfig)
    coordinate_mapping: CoordinateMappingConfig = field(default_factory=CoordinateMappingConfig)
    vehicle_limits: VehicleLimitsConfig = field(default_factory=VehicleLimitsConfig)
    control: ControlLoopConfig = field(default_factory=ControlLoopConfig)
    td3: TD3Config = field(default_factory=TD3Config)
    reward: RewardConfig = field(default_factory=RewardConfig)
    curriculum: CurriculumConfig = field(default_factory=CurriculumConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_controller_config(path: Optional[str | Path] = None) -> ControllerConfig:
    """Load controller configuration from JSON file, falling back to defaults."""
    if path is None:
        return ControllerConfig()
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Controller configuration file not found: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return ControllerConfig(
        airsim=AirSimConfig(**raw.get("airsim", {})),
        coordinate_mapping=CoordinateMappingConfig(**raw.get("coordinate_mapping", {})),
        vehicle_limits=VehicleLimitsConfig(**raw.get("vehicle_limits", {})),
        control=ControlLoopConfig(**raw.get("control", {})),
        td3=TD3Config(**raw.get("td3", {})),
        reward=RewardConfig(**raw.get("reward", {})),
        curriculum=CurriculumConfig(**raw.get("curriculum", {})),
        paths=PathsConfig(**raw.get("paths", {})),
    )


def load_safety_config(path: Optional[str | Path] = None) -> SafetyConfig:
    """Load fuzzy safety configuration from JSON file, falling back to defaults."""
    if path is None:
        cfg = SafetyConfig()
        cfg.validate()
        return cfg
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Safety configuration file not found: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    membership_raw = raw.get("membership", {})
    raw_copy = {k: v for k, v in raw.items() if k != "membership"}
    cfg = SafetyConfig(
        membership=FuzzyMembershipConfig(**membership_raw),
        **raw_copy,
    )
    cfg.validate()
    return cfg
