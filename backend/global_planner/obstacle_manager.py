"""Obstacle representations and collision detection for UAV route planning.

Supports circular obstacles, rectangular obstacles, and dynamic obstacle snapshots
with exact geometric distance computations and configurable safety clearance buffers.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import numpy as np


class BaseObstacle(ABC):
    """Abstract base class for all obstacle geometries."""

    def __init__(self, obstacle_id: str, is_dynamic: bool = False):
        self.id = obstacle_id
        self.is_dynamic = is_dynamic

    @abstractmethod
    def point_collides(self, x: float, y: float, clearance: float = 0.0) -> bool:
        """Return True if point (x, y) lies inside the obstacle or its clearance zone."""
        pass

    @abstractmethod
    def segment_collides(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        clearance: float = 0.0,
    ) -> bool:
        """Return True if line segment (p1, p2) collides with obstacle or clearance zone."""
        pass

    @abstractmethod
    def distance_to_point(self, x: float, y: float) -> float:
        """Return Euclidean distance from (x, y) to obstacle boundary.

        Returns negative value if point is inside the obstacle.
        """
        pass

    @abstractmethod
    def get_bounding_box(self, clearance: float = 0.0) -> Tuple[float, float, float, float]:
        """Return (x_min, x_max, y_min, y_max) enclosing obstacle plus clearance."""
        pass


class CircularObstacle(BaseObstacle):
    """Circular obstacle defined by center (x, y) and radius r."""

    def __init__(
        self,
        obstacle_id: str,
        x: float,
        y: float,
        radius: float,
        is_dynamic: bool = False,
    ):
        super().__init__(obstacle_id, is_dynamic)
        if radius <= 0.0:
            raise ValueError(f"Circular obstacle {obstacle_id} radius must be > 0. Got {radius}")
        self.x = float(x)
        self.y = float(y)
        self.radius = float(radius)

    def point_collides(self, x: float, y: float, clearance: float = 0.0) -> bool:
        effective_r = self.radius + max(0.0, clearance)
        dx = x - self.x
        dy = y - self.y
        return (dx * dx + dy * dy) <= (effective_r * effective_r)

    def distance_to_point(self, x: float, y: float) -> float:
        dx = x - self.x
        dy = y - self.y
        dist_to_center = math.hypot(dx, dy)
        return dist_to_center - self.radius

    def segment_collides(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        clearance: float = 0.0,
    ) -> bool:
        """Check if line segment p1->p2 collides with circle inflated by clearance."""
        effective_r = self.radius + max(0.0, clearance)
        x1, y1 = p1
        x2, y2 = p2
        dx = x2 - x1
        dy = y2 - y1
        seg_len_sq = dx * dx + dy * dy

        if seg_len_sq < 1e-12:
            # Segment is a single point
            return self.point_collides(x1, y1, clearance)

        # Project circle center onto segment line parameterized by t in [0, 1]
        t = ((self.x - x1) * dx + (self.y - y1) * dy) / seg_len_sq
        t_clamped = max(0.0, min(1.0, t))

        closest_x = x1 + t_clamped * dx
        closest_y = y1 + t_clamped * dy

        dist_sq = (self.x - closest_x) ** 2 + (self.y - closest_y) ** 2
        return dist_sq <= (effective_r * effective_r)

    def get_bounding_box(self, clearance: float = 0.0) -> Tuple[float, float, float, float]:
        effective_r = self.radius + max(0.0, clearance)
        return (
            self.x - effective_r,
            self.x + effective_r,
            self.y - effective_r,
            self.y + effective_r,
        )


class RectangularObstacle(BaseObstacle):
    """Axis-aligned rectangular obstacle defined by [x_min, x_max, y_min, y_max]."""

    def __init__(
        self,
        obstacle_id: str,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        is_dynamic: bool = False,
    ):
        super().__init__(obstacle_id, is_dynamic)
        if x_max <= x_min or y_max <= y_min:
            raise ValueError(
                f"Invalid rectangle bounds for {obstacle_id}: [{x_min}, {x_max}, {y_min}, {y_max}]"
            )
        self.x_min = float(x_min)
        self.x_max = float(x_max)
        self.y_min = float(y_min)
        self.y_max = float(y_max)

    def point_collides(self, x: float, y: float, clearance: float = 0.0) -> bool:
        """Collision check using exact Minkowski sum (rectangle expanded with round corners)."""
        return self.distance_to_point(x, y) <= max(0.0, clearance)

    def distance_to_point(self, x: float, y: float) -> float:
        """Exact signed distance from point to axis-aligned box."""
        dx = max(0.0, self.x_min - x, x - self.x_max)
        dy = max(0.0, self.y_min - y, y - self.y_max)

        if dx > 0.0 or dy > 0.0:
            # Outside the rectangle
            return math.hypot(dx, dy)

        # Inside the rectangle - negative distance to closest boundary
        dist_left = x - self.x_min
        dist_right = self.x_max - x
        dist_bottom = y - self.y_min
        dist_top = self.y_max - y
        return -min(dist_left, dist_right, dist_bottom, dist_top)

    def segment_collides(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        clearance: float = 0.0,
    ) -> bool:
        """Check collision between segment and rectangle with safety clearance.

        Uses exact swept-sphere / distance check between line segment and box.
        """
        # If either endpoint collides:
        if self.point_collides(p1[0], p1[1], clearance) or self.point_collides(p2[0], p2[1], clearance):
            return True

        # Quick rejection using expanded bounding box
        seg_min_x = min(p1[0], p2[0])
        seg_max_x = max(p1[0], p2[0])
        seg_min_y = min(p1[1], p2[1])
        seg_max_y = max(p1[1], p2[1])

        eff_x_min = self.x_min - clearance
        eff_x_max = self.x_max + clearance
        eff_y_min = self.y_min - clearance
        eff_y_max = self.y_max + clearance

        if (
            seg_max_x < eff_x_min
            or seg_min_x > eff_x_max
            or seg_max_y < eff_y_min
            or seg_min_y > eff_y_max
        ):
            return False

        # Check line segment intersection with original rectangle edges
        rect_edges = [
            ((self.x_min, self.y_min), (self.x_max, self.y_min)),
            ((self.x_max, self.y_min), (self.x_max, self.y_max)),
            ((self.x_max, self.y_max), (self.x_min, self.y_max)),
            ((self.x_min, self.y_max), (self.x_min, self.y_min)),
        ]

        for e1, e2 in rect_edges:
            if _segments_intersect(p1, p2, e1, e2):
                return True

        # If clearance > 0, check distance from segment to the 4 corners of rectangle
        # and distance from segment to the 4 edges
        if clearance > 0.0:
            corners = [
                (self.x_min, self.y_min),
                (self.x_max, self.y_min),
                (self.x_max, self.y_max),
                (self.x_min, self.y_max),
            ]
            for cx, cy in corners:
                if _dist_point_to_segment((cx, cy), p1, p2) <= clearance:
                    return True

            for e1, e2 in rect_edges:
                if _dist_segment_to_segment(p1, p2, e1, e2) <= clearance:
                    return True

        return False

    def get_bounding_box(self, clearance: float = 0.0) -> Tuple[float, float, float, float]:
        eff = max(0.0, clearance)
        return (
            self.x_min - eff,
            self.x_max + eff,
            self.y_min - eff,
            self.y_max + eff,
        )


def _segments_intersect(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    p4: Tuple[float, float],
) -> bool:
    """Return True if line segments p1-p2 and p3-p4 intersect."""
    def ccw(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])

    ccw1 = ccw(p1, p3, p4)
    ccw2 = ccw(p2, p3, p4)
    ccw3 = ccw(p1, p2, p3)
    ccw4 = ccw(p1, p2, p4)

    if ((ccw1 > 0 and ccw2 < 0) or (ccw1 < 0 and ccw2 > 0)) and \
       ((ccw3 > 0 and ccw4 < 0) or (ccw3 < 0 and ccw4 > 0)):
        return True

    # Collinear/touching checks
    def on_segment(p: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]) -> bool:
        return (
            min(a[0], b[0]) - 1e-9 <= p[0] <= max(a[0], b[0]) + 1e-9
            and min(a[1], b[1]) - 1e-9 <= p[1] <= max(a[1], b[1]) + 1e-9
        )

    if abs(ccw1) < 1e-9 and on_segment(p1, p3, p4):
        return True
    if abs(ccw2) < 1e-9 and on_segment(p2, p3, p4):
        return True
    if abs(ccw3) < 1e-9 and on_segment(p3, p1, p2):
        return True
    if abs(ccw4) < 1e-9 and on_segment(p4, p1, p2):
        return True

    return False


def _dist_point_to_segment(
    pt: Tuple[float, float],
    seg1: Tuple[float, float],
    seg2: Tuple[float, float],
) -> float:
    """Return Euclidean distance from point pt to segment seg1-seg2."""
    x1, y1 = seg1
    x2, y2 = seg2
    dx = x2 - x1
    dy = y2 - y1
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq < 1e-12:
        return math.hypot(pt[0] - x1, pt[1] - y1)
    t = ((pt[0] - x1) * dx + (pt[1] - y1) * dy) / seg_len_sq
    t_clamped = max(0.0, min(1.0, t))
    closest_x = x1 + t_clamped * dx
    closest_y = y1 + t_clamped * dy
    return math.hypot(pt[0] - closest_x, pt[1] - closest_y)


def _dist_segment_to_segment(
    s1_p1: Tuple[float, float],
    s1_p2: Tuple[float, float],
    s2_p1: Tuple[float, float],
    s2_p2: Tuple[float, float],
) -> float:
    """Return minimum Euclidean distance between two line segments."""
    if _segments_intersect(s1_p1, s1_p2, s2_p1, s2_p2):
        return 0.0
    return min(
        _dist_point_to_segment(s1_p1, s2_p1, s2_p2),
        _dist_point_to_segment(s1_p2, s2_p1, s2_p2),
        _dist_point_to_segment(s2_p1, s1_p1, s1_p2),
        _dist_point_to_segment(s2_p2, s1_p1, s1_p2),
    )


class ObstacleManager:
    """Manages all obstacles in the environment, collision queries, and clearance buffers."""

    def __init__(self, default_clearance: float = 2.0):
        self.default_clearance = max(0.0, float(default_clearance))
        self.obstacles: List[BaseObstacle] = []

    def add_obstacle(self, obstacle: BaseObstacle) -> None:
        self.obstacles.append(obstacle)

    def add_circular_obstacle(
        self,
        obstacle_id: str,
        x: float,
        y: float,
        radius: float,
        is_dynamic: bool = False,
    ) -> CircularObstacle:
        obs = CircularObstacle(obstacle_id, x, y, radius, is_dynamic=is_dynamic)
        self.add_obstacle(obs)
        return obs

    def add_rectangular_obstacle(
        self,
        obstacle_id: str,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        is_dynamic: bool = False,
    ) -> RectangularObstacle:
        obs = RectangularObstacle(obstacle_id, x_min, x_max, y_min, y_max, is_dynamic=is_dynamic)
        self.add_obstacle(obs)
        return obs

    def clear(self) -> None:
        self.obstacles.clear()

    def point_collides(
        self,
        x: float,
        y: float,
        clearance: Optional[float] = None,
    ) -> bool:
        """Check if point (x, y) collides with any obstacle considering safety clearance."""
        eff_clearance = self.default_clearance if clearance is None else clearance
        return any(obs.point_collides(x, y, eff_clearance) for obs in self.obstacles)

    def segment_collides(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        clearance: Optional[float] = None,
    ) -> bool:
        """Check if line segment p1-p2 collides with any obstacle considering safety clearance."""
        eff_clearance = self.default_clearance if clearance is None else clearance
        return any(obs.segment_collides(p1, p2, eff_clearance) for obs in self.obstacles)

    def min_distance_to_obstacles(self, x: float, y: float) -> float:
        """Return the minimum distance from point (x, y) to any obstacle boundary.

        Returns float('inf') if there are no obstacles.
        """
        if not self.obstacles:
            return float("inf")
        return min(obs.distance_to_point(x, y) for obs in self.obstacles)

    def min_distance_along_path(self, path: List[Tuple[float, float]]) -> float:
        """Return the minimum clearance to obstacle boundaries along a continuous path."""
        if not self.obstacles or not path:
            return float("inf")

        min_dist = float("inf")
        # Check all waypoints and intermediate segment samples
        for i in range(len(path) - 1):
            p1 = path[i]
            p2 = path[i + 1]
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            # Sample at least every 0.5 units or 10 samples per segment
            num_samples = max(2, int(math.ceil(seg_len / 0.5)))
            for s in range(num_samples + 1):
                t = s / num_samples
                sx = p1[0] + t * (p2[0] - p1[0])
                sy = p1[1] + t * (p2[1] - p1[1])
                dist = self.min_distance_to_obstacles(sx, sy)
                if dist < min_dist:
                    min_dist = dist
        return min_dist

    def rasterize_grid(
        self,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        grid_resolution: float,
        clearance: Optional[float] = None,
    ) -> Tuple[np.ndarray, int, int]:
        """Generate a 2D boolean occupancy grid where True indicates blocked/obstacle.

        Returns: (occupancy_grid, width_cells, height_cells)
        """
        eff_clearance = self.default_clearance if clearance is None else clearance
        width = int(math.ceil((x_max - x_min) / grid_resolution)) + 1
        height = int(math.ceil((y_max - y_min) / grid_resolution)) + 1

        occupancy = np.zeros((height, width), dtype=bool)

        # Vectorized or fast bounding-box evaluation for each obstacle
        for obs in self.obstacles:
            bx_min, bx_max, by_min, by_max = obs.get_bounding_box(eff_clearance)
            # Find index bounds
            col_min = max(0, int(math.floor((bx_min - x_min) / grid_resolution)))
            col_max = min(width - 1, int(math.ceil((bx_max - x_min) / grid_resolution)))
            row_min = max(0, int(math.floor((by_min - y_min) / grid_resolution)))
            row_max = min(height - 1, int(math.ceil((by_max - y_min) / grid_resolution)))

            for r in range(row_min, row_max + 1):
                py = y_min + r * grid_resolution
                for c in range(col_min, col_max + 1):
                    if occupancy[r, c]:
                        continue
                    px = x_min + c * grid_resolution
                    if obs.point_collides(px, py, eff_clearance):
                        occupancy[r, c] = True

        return occupancy, width, height
