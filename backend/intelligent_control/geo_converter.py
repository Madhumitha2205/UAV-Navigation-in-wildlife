"""Geographical Coordinate Conversion for UAV India Navigation System.

Provides bi-directional conversion between real WGS84 geographical coordinates
(Latitude, Longitude, Altitude) and local simulation coordinate frames (ENU in metres and AirSim NED).

Uses standard Local Tangent Plane (LTP) projection centered on a mission reference origin.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple


WGS84_A = 6378137.0  # Semi-major axis (metres)
WGS84_F = 1.0 / 298.257223563  # Flattening
WGS84_E2 = 2.0 * WGS84_F - WGS84_F * WGS84_F  # First eccentricity squared
METRES_PER_DEGREE_LAT = 111319.9  # Standard spherical approximation baseline


@dataclass(frozen=True)
class GeoPoint:
    """Geographical coordinate on the Earth's surface."""
    lat: float  # Latitude in decimal degrees (e.g., 20.5937 N)
    lon: float  # Longitude in decimal degrees (e.g., 78.9629 E)
    alt: float = 10.0  # Altitude above ground in metres

    def to_dict(self) -> Dict[str, float]:
        return {"lat": round(self.lat, 6), "lon": round(self.lon, 6), "alt": round(self.alt, 2)}

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "GeoPoint":
        return cls(
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            alt=float(data.get("alt", 10.0)),
        )


def haversine_distance_m(p1: GeoPoint, p2: GeoPoint) -> float:
    """Calculate the great-circle distance between two GPS points in metres."""
    lat1_rad = math.radians(p1.lat)
    lat2_rad = math.radians(p2.lat)
    dlat = math.radians(p2.lat - p1.lat)
    dlon = math.radians(p2.lon - p1.lon)

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return WGS84_A * c


def initial_bearing_deg(p1: GeoPoint, p2: GeoPoint) -> float:
    """Calculate initial compass bearing from p1 to p2 in degrees [0, 360)."""
    lat1_rad = math.radians(p1.lat)
    lat2_rad = math.radians(p2.lat)
    dlon_rad = math.radians(p2.lon - p1.lon)

    y = math.sin(dlon_rad) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
    brng = math.degrees(math.atan2(y, x))
    return (brng + 360.0) % 360.0


class GeoCoordinateConverter:
    """Bi-directional Local Tangent Plane (ENU) to GPS (Lat/Lon) Converter.

    Projects geographic coordinates onto a local Cartesian East-North-Up (ENU) plane
    centered at `origin_gps`. This enables the global planner (GA, 2-Opt, A*) and local
    controllers (TD3, AFL) to operate in metric space while maintaining full fidelity
    with real-world India map coordinates.
    """

    def __init__(self, origin_gps: GeoPoint, scale_factor: float = 1.0) -> None:
        """Initialize converter.

        Args:
            origin_gps: Reference geographic anchor (lat0, lon0, alt0).
            scale_factor: Optional scaling factor when mapping continental corridor
                          distances into tactical simulation boundaries.
        """
        self.origin = origin_gps
        self.scale_factor = max(scale_factor, 1e-6)

        # Radians
        self._lat0_rad = math.radians(origin_gps.lat)
        self._lon0_rad = math.radians(origin_gps.lon)

        # Metres per degree at reference latitude using WGS-84 ellipsoid radius of curvature
        sin_lat = math.sin(self._lat0_rad)
        n_rad = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
        m_rad = (WGS84_A * (1.0 - WGS84_E2)) / math.pow(1.0 - WGS84_E2 * sin_lat * sin_lat, 1.5)

        self._metres_per_deg_lat = (math.pi / 180.0) * m_rad
        self._metres_per_deg_lon = (math.pi / 180.0) * n_rad * math.cos(self._lat0_rad)

        if abs(self._metres_per_deg_lon) < 1e-4:
            self._metres_per_deg_lon = 1e-4

    def gps_to_enu(self, point: GeoPoint) -> Tuple[float, float, float]:
        """Convert GPS coordinate (lat, lon, alt) to local ENU coordinate (x_east, y_north, z_up).

        Applies scaling if configured so missions across India scale into the simulation grid.
        """
        d_lat = point.lat - self.origin.lat
        d_lon = point.lon - self.origin.lon

        east_m = (d_lon * self._metres_per_deg_lon) * self.scale_factor
        north_m = (d_lat * self._metres_per_deg_lat) * self.scale_factor
        up_m = point.alt

        return round(east_m, 4), round(north_m, 4), round(up_m, 4)

    def enu_to_gps(self, x_east: float, y_north: float, z_up: float = 10.0) -> GeoPoint:
        """Convert local ENU coordinate (x_east, y_north, z_up) back to real GPS coordinate."""
        raw_east = x_east / self.scale_factor
        raw_north = y_north / self.scale_factor

        d_lat = raw_north / self._metres_per_deg_lat
        d_lon = raw_east / self._metres_per_deg_lon

        lat = self.origin.lat + d_lat
        lon = self.origin.lon + d_lon
        alt = z_up

        return GeoPoint(lat=round(lat, 7), lon=round(lon, 7), alt=round(alt, 2))

    @classmethod
    def fit_converter_for_route(
        cls,
        waypoints: Sequence[GeoPoint],
        target_grid_size: float = 100.0,
        padding: float = 10.0,
    ) -> Tuple["GeoCoordinateConverter", float, float, float, float]:
        """Automatically construct a converter that comfortably fits a sequence of GPS waypoints.

        Returns:
            converter: Initialized converter with anchor at the route bounding box center or start.
            origin_x: Local offset for grid alignment.
            origin_y: Local offset for grid alignment.
            width: Required grid width.
            height: Required grid height.
        """
        if not waypoints:
            origin = GeoPoint(lat=20.5937, lon=78.9629, alt=10.0)
            return cls(origin), 0.0, 0.0, target_grid_size, target_grid_size

        origin = waypoints[0]
        temp_converter = cls(origin, scale_factor=1.0)
        enu_pts = [temp_converter.gps_to_enu(p) for p in waypoints]

        xs = [p[0] for p in enu_pts]
        ys = [p[1] for p in enu_pts]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        span_x = max(max_x - min_x, 10.0)
        span_y = max(max_y - min_y, 10.0)
        max_span = max(span_x, span_y)

        # Scale factor so the maximum span maps into the target grid area
        scale = (target_grid_size - 2.0 * padding) / max_span
        scaled_converter = cls(origin, scale_factor=scale)

        return scaled_converter, min_x * scale, min_y * scale, span_x * scale + 2 * padding, span_y * scale + 2 * padding
