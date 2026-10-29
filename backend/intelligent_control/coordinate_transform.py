"""Explicit coordinate transformation between Global Planner (ENU/Altitude-Up) and AirSim (NED).

Mapping convention (configurable via CoordinateMappingConfig):
- Global Planner: (X, Y, Z) where default X = East (m), Y = North (m), Z = Altitude positive UP (m).
- AirSim Multirotor: (North, East, Down) where North = +X_ned, East = +Y_ned, Down = +Z_ned (-Altitude).

Linear transformation:
  [North]   [x_to_north  y_to_north  0]   ( [X] - [origin_planner_x] )   [origin_ned_n]
  [East ] = [x_to_east   y_to_east   0] * ( [Y] - [origin_planner_y] ) + [origin_ned_e]
  [Down ]   [0           0      z_sign]   ( [Z] - [origin_planner_z] )   [origin_ned_d]
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple
import numpy as np

from backend.intelligent_control.config import CoordinateMappingConfig
from backend.intelligent_control.route_loader import GlobalRoute, RoutePoint, StaticObstacleSpec


class CoordinateTransformer:
    """Bi-directional coordinate transformer between Global Planner and AirSim frames."""

    def __init__(self, config: CoordinateMappingConfig | None = None) -> None:
        self.config = config or CoordinateMappingConfig()
        self.scale = float(self.config.scale)
        if self.scale <= 0.0:
            raise ValueError("Coordinate scale must be strictly positive.")

        # 2x2 horizontal transformation matrix M: [North, East]^T = M @ [dx, dy]^T
        self._horiz_matrix = np.array(
            [
                [float(self.config.x_to_north), float(self.config.y_to_north)],
                [float(self.config.x_to_east), float(self.config.y_to_east)],
            ],
            dtype=np.float64,
        )
        det = float(np.linalg.det(self._horiz_matrix))
        if abs(det) < 1e-8:
            raise ValueError("Horizontal coordinate mapping matrix is singular (non-invertible).")
        self._horiz_inv = np.linalg.inv(self._horiz_matrix)

        self._z_sign = float(self.config.z_sign)
        if abs(self._z_sign) < 1e-8:
            raise ValueError("z_sign must be non-zero (-1.0 for NED when planner Z is altitude-up).")

        self._origin_planner = np.array(self.config.origin_planner, dtype=np.float64)
        self._origin_ned = np.array(self.config.origin_ned, dtype=np.float64)

    def planner_to_airsim_pos(self, pos_xyz: Sequence[float]) -> Tuple[float, float, float]:
        """Convert planner position (X, Y, Z_up) to AirSim NED position (North, East, Down)."""
        if len(pos_xyz) != 3:
            raise ValueError(f"Expected 3D position, got length {len(pos_xyz)}.")
        vec = (np.asarray(pos_xyz, dtype=np.float64) - self._origin_planner) * self.scale
        ne = self._horiz_matrix @ vec[:2]
        down = self._z_sign * vec[2]
        ned = np.array([ne[0], ne[1], down], dtype=np.float64) + self._origin_ned
        return float(ned[0]), float(ned[1]), float(ned[2])

    def airsim_to_planner_pos(self, pos_ned: Sequence[float]) -> Tuple[float, float, float]:
        """Convert AirSim NED position (North, East, Down) to planner position (X, Y, Z_up)."""
        if len(pos_ned) != 3:
            raise ValueError(f"Expected 3D NED position, got length {len(pos_ned)}.")
        vec_ned = (np.asarray(pos_ned, dtype=np.float64) - self._origin_ned) / self.scale
        xy = self._horiz_inv @ vec_ned[:2]
        z_up = vec_ned[2] / self._z_sign
        xyz = np.array([xy[0], xy[1], z_up], dtype=np.float64) + self._origin_planner
        return float(xyz[0]), float(xyz[1]), float(xyz[2])

    def planner_to_airsim_vel(self, vel_xyz: Sequence[float]) -> Tuple[float, float, float]:
        """Convert planner velocity (vx, vy, vz_up) to AirSim NED velocity (vn, ve, vd)."""
        if len(vel_xyz) != 3:
            raise ValueError(f"Expected 3D velocity, got length {len(vel_xyz)}.")
        vec = np.asarray(vel_xyz, dtype=np.float64) * self.scale
        ne = self._horiz_matrix @ vec[:2]
        vd = self._z_sign * vec[2]
        return float(ne[0]), float(ne[1]), float(vd)

    def airsim_to_planner_vel(self, vel_ned: Sequence[float]) -> Tuple[float, float, float]:
        """Convert AirSim NED velocity (vn, ve, vd) to planner velocity (vx, vy, vz_up)."""
        if len(vel_ned) != 3:
            raise ValueError(f"Expected 3D NED velocity, got length {len(vel_ned)}.")
        vec_ned = np.asarray(vel_ned, dtype=np.float64) / self.scale
        xy = self._horiz_inv @ vec_ned[:2]
        vz_up = vec_ned[2] / self._z_sign
        return float(xy[0]), float(xy[1]), float(vz_up)

    def convert_route_points_to_airsim(self, points: Iterable[RoutePoint]) -> List[Tuple[float, float, float]]:
        """Convert an iterable of RoutePoints from planner coordinates to AirSim NED tuples."""
        return [self.planner_to_airsim_pos((pt.x, pt.y, pt.z)) for pt in points]

    def convert_obstacles_to_airsim(
        self, obstacles: Iterable[StaticObstacleSpec]
    ) -> List[Tuple[float, float, float, float]]:
        """Convert obstacle positions and radii to AirSim NED (north, east, down, radius)."""
        converted = []
        for obs in obstacles:
            n, e, d = self.planner_to_airsim_pos((obs.x, obs.y, obs.z))
            converted.append((n, e, d, obs.radius * self.scale))
        return converted
