"""AirSim Sensor Reader and Validation Module.

Reads simulated LiDAR point clouds and collision status from AirSim, or computes
validated relative obstacle geometry from explicit scenario obstacles when LiDAR
is not configured in the simulator settings. Never fabricates hidden readings:
the active sensor mode ('LIDAR', 'GEOMETRIC_SCENARIO_FALLBACK', or 'UNAVAILABLE')
is explicitly recorded on every observation.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple
import numpy as np

from backend.intelligent_control.airsim_client import AirSimUAVClient
from backend.intelligent_control.config import AirSimConfig

logger = logging.getLogger(__name__)


@dataclass
class ObstacleObservation:
    """Validated obstacle & collision observation in the planner coordinate frame."""
    sensor_mode: str  # 'LIDAR', 'GEOMETRIC_SCENARIO_FALLBACK', or 'UNAVAILABLE'
    is_valid: bool
    has_collided: bool
    closest_distance_m: float
    # Unit direction vector pointing FROM the closest obstacle TOWARD the UAV (repulsion vector)
    repulsion_unit_xyz: Tuple[float, float, float]
    # Relative vector from UAV to closest obstacle surface (obstacle_pos - uav_pos)
    obstacle_rel_xyz: Tuple[float, float, float]
    # Closing speed (m/s) toward the closest obstacle (>0 means approaching)
    closing_speed_mps: float
    num_detected_points: int = 0
    collided_object_name: str = ""
    notes: str = ""


class AirSimSensorReader:
    """Reads LiDAR and collision telemetry from AirSim with explicit fallback modes."""

    def __init__(
        self,
        config: Optional[AirSimConfig] = None,
        max_lidar_range_m: float = 50.0,
    ) -> None:
        self.config = config or AirSimConfig()
        self.max_lidar_range_m = float(max_lidar_range_m)

    def read_collision_info(self, uav_client: AirSimUAVClient) -> Tuple[bool, str]:
        """Read collision information from the connected AirSim client."""
        try:
            col_info = uav_client.raw_client.simGetCollisionInfo(
                vehicle_name=self.config.vehicle_name
            )
            has_collided = bool(getattr(col_info, "has_collided", False))
            obj_name = str(getattr(col_info, "object_name", "")) if has_collided else ""
            return has_collided, obj_name
        except Exception as exc:
            logger.warning("Failed to read AirSim collision info: %s", exc)
            return False, ""

    def read_lidar_points_ned(self, uav_client: AirSimUAVClient) -> Optional[np.ndarray]:
        """Read 3D LiDAR point cloud from AirSim.

        Returns an (N, 3) numpy array of finite points in the sensor/vehicle frame,
        or None if LiDAR is unconfigured, invalid, or returns an empty cloud.
        """
        try:
            lidar_data = uav_client.raw_client.getLidarData(
                lidar_name=self.config.lidar_sensor_name,
                vehicle_name=self.config.vehicle_name,
            )
            raw_cloud = getattr(lidar_data, "point_cloud", None)
            if not raw_cloud or len(raw_cloud) < 3:
                return None
            pts = np.asarray(raw_cloud, dtype=np.float64)
            usable_len = (len(pts) // 3) * 3
            if usable_len == 0:
                return None
            pts = pts[:usable_len].reshape(-1, 3)
            # Filter non-finite or zero-origin artifact points
            finite_mask = np.all(np.isfinite(pts), axis=1)
            pts = pts[finite_mask]
            if len(pts) == 0:
                return None
            norms = np.linalg.norm(pts, axis=1)
            valid_range = (norms > 0.05) & (norms <= self.max_lidar_range_m)
            pts = pts[valid_range]
            return pts if len(pts) > 0 else None
        except Exception as exc:
            logger.debug("LiDAR sensor '%s' unavailable or unconfigured: %s", self.config.lidar_sensor_name, exc)
            return None

    def compute_observation_from_points(
        self,
        relative_points_xyz: np.ndarray,
        uav_vel_xyz: Sequence[float],
        has_collided: bool = False,
        sensor_mode: str = "LIDAR",
    ) -> ObstacleObservation:
        """Compute closest obstacle metrics from relative obstacle points in planner frame."""
        if relative_points_xyz is None or len(relative_points_xyz) == 0:
            return ObstacleObservation(
                sensor_mode=sensor_mode,
                is_valid=True,
                has_collided=has_collided,
                closest_distance_m=self.max_lidar_range_m,
                repulsion_unit_xyz=(0.0, 0.0, 0.0),
                obstacle_rel_xyz=(self.max_lidar_range_m, 0.0, 0.0),
                closing_speed_mps=0.0,
                num_detected_points=0,
                notes="No obstacles within detection range.",
            )

        pts = np.asarray(relative_points_xyz, dtype=np.float64)
        if pts.ndim != 2 or pts.shape[1] != 3 or not np.all(np.isfinite(pts)):
            return ObstacleObservation(
                sensor_mode="UNAVAILABLE",
                is_valid=False,
                has_collided=has_collided,
                closest_distance_m=float("nan"),
                repulsion_unit_xyz=(0.0, 0.0, 0.0),
                obstacle_rel_xyz=(0.0, 0.0, 0.0),
                closing_speed_mps=0.0,
                num_detected_points=0,
                notes="Invalid or non-finite sensor point array.",
            )

        dists = np.linalg.norm(pts, axis=1)
        min_idx = int(np.argmin(dists))
        min_dist = float(dists[min_idx])
        closest_rel = pts[min_idx]  # vector from UAV to obstacle

        if min_dist > 1e-6:
            unit_to_obs = closest_rel / min_dist
            repulsion = -unit_to_obs
        else:
            unit_to_obs = np.array([1.0, 0.0, 0.0], dtype=np.float64)
            repulsion = np.array([-1.0, 0.0, 1.0], dtype=np.float64)
            repulsion /= np.linalg.norm(repulsion)

        vel = np.asarray(uav_vel_xyz, dtype=np.float64)
        closing_speed = float(np.dot(vel, unit_to_obs))

        return ObstacleObservation(
            sensor_mode=sensor_mode,
            is_valid=True,
            has_collided=has_collided,
            closest_distance_m=min(min_dist, self.max_lidar_range_m),
            repulsion_unit_xyz=(float(repulsion[0]), float(repulsion[1]), float(repulsion[2])),
            obstacle_rel_xyz=(float(closest_rel[0]), float(closest_rel[1]), float(closest_rel[2])),
            closing_speed_mps=closing_speed,
            num_detected_points=int(len(pts)),
        )

    def compute_observation_from_spheres(
        self,
        uav_pos_xyz: Sequence[float],
        uav_vel_xyz: Sequence[float],
        obstacles_xyz_r: Sequence[Tuple[float, float, float, float]],
        obstacle_vels_xyz: Optional[Sequence[Tuple[float, float, float]]] = None,
        uav_radius_m: float = 0.5,
        sensor_mode: str = "GEOMETRIC_SCENARIO_FALLBACK",
    ) -> ObstacleObservation:
        """Compute validated obstacle observation from spherical obstacles (center x, y, z, radius)."""
        pos = np.asarray(uav_pos_xyz, dtype=np.float64)
        vel = np.asarray(uav_vel_xyz, dtype=np.float64)

        if not np.all(np.isfinite(pos)) or not np.all(np.isfinite(vel)):
            return ObstacleObservation(
                sensor_mode="UNAVAILABLE",
                is_valid=False,
                has_collided=False,
                closest_distance_m=float("nan"),
                repulsion_unit_xyz=(0.0, 0.0, 0.0),
                obstacle_rel_xyz=(0.0, 0.0, 0.0),
                closing_speed_mps=0.0,
                notes="Non-finite UAV state input.",
            )

        if not obstacles_xyz_r:
            return ObstacleObservation(
                sensor_mode=sensor_mode,
                is_valid=True,
                has_collided=False,
                closest_distance_m=self.max_lidar_range_m,
                repulsion_unit_xyz=(0.0, 0.0, 0.0),
                obstacle_rel_xyz=(self.max_lidar_range_m, 0.0, 0.0),
                closing_speed_mps=0.0,
                num_detected_points=0,
                notes="Clear surroundings (no obstacles configured).",
            )

        closest_surface_dist = self.max_lidar_range_m
        closest_rel_vec = np.array([self.max_lidar_range_m, 0.0, 0.0], dtype=np.float64)
        closest_repulsion = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        closest_closing_speed = 0.0
        has_collided = False
        collided_name = ""

        for idx, obs in enumerate(obstacles_xyz_r):
            ox, oy, oz, radius = float(obs[0]), float(obs[1]), float(obs[2]), float(obs[3])
            obs_center = np.array([ox, oy, oz], dtype=np.float64)
            if not np.all(np.isfinite(obs_center)) or radius <= 0.0 or not math.isfinite(radius):
                return ObstacleObservation(
                    sensor_mode="UNAVAILABLE",
                    is_valid=False,
                    has_collided=False,
                    closest_distance_m=float("nan"),
                    repulsion_unit_xyz=(0.0, 0.0, 0.0),
                    obstacle_rel_xyz=(0.0, 0.0, 0.0),
                    closing_speed_mps=0.0,
                    notes=f"Invalid obstacle definition at index {idx}.",
                )

            rel_center = obs_center - pos
            center_dist = float(np.linalg.norm(rel_center))
            surface_dist = max(0.0, center_dist - radius)

            if center_dist <= (radius + uav_radius_m):
                has_collided = True
                collided_name = f"OBS_{idx}"

            if surface_dist < closest_surface_dist:
                closest_surface_dist = surface_dist
                if center_dist > 1e-6:
                    unit_to_obs = rel_center / center_dist
                    closest_repulsion = -unit_to_obs
                    closest_rel_vec = unit_to_obs * surface_dist
                else:
                    unit_to_obs = np.array([1.0, 0.0, 0.0], dtype=np.float64)
                    closest_repulsion = np.array([-1.0, 0.0, 0.0], dtype=np.float64)
                    closest_rel_vec = np.zeros(3, dtype=np.float64)

                obs_vel = (
                    np.asarray(obstacle_vels_xyz[idx], dtype=np.float64)
                    if obstacle_vels_xyz is not None and idx < len(obstacle_vels_xyz)
                    else np.zeros(3, dtype=np.float64)
                )
                rel_vel = vel - obs_vel
                closest_closing_speed = float(np.dot(rel_vel, unit_to_obs))

        return ObstacleObservation(
            sensor_mode=sensor_mode,
            is_valid=True,
            has_collided=has_collided,
            closest_distance_m=float(closest_surface_dist),
            repulsion_unit_xyz=(
                float(closest_repulsion[0]),
                float(closest_repulsion[1]),
                float(closest_repulsion[2]),
            ),
            obstacle_rel_xyz=(
                float(closest_rel_vec[0]),
                float(closest_rel_vec[1]),
                float(closest_rel_vec[2]),
            ),
            closing_speed_mps=float(closest_closing_speed),
            num_detected_points=len(obstacles_xyz_r),
            collided_object_name=collided_name,
        )
