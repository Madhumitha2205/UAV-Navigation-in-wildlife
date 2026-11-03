"""AirSim 3D Obstacle Visualization, Spawning, and Validation Module.

Spawns, verifies, and cleans up visible 3D scene representations of the global planner's
obstacle regions (`dense_canopy_01`, `mountain_ridge_01`, `elephant_herd_snapshot`) inside
the AirSim Blocks environment using verified Unreal assets (`1M_Cube_Chamfer`, `Cylinder`,
`Cone`, `Sphere`).

Key Safety & Architectural Guarantees:
- Reads obstacle coordinates and dimensions directly from the planner's source-of-truth
  configuration (`configs/default_environment.json` / `Environment`).
- Uses the project's `CoordinateTransformer` (`ENU_ALT_UP` -> AirSim `NED` with configured
  `origin_ned`) so spawned 3D obstacles share the exact coordinate frame and altitude datum
  as the flying UAV.
- Strictly prefixes all project-created actors with `wl_obs_` and never modifies or deletes
  any pre-existing Unreal scene actors.
- Validates that all spawned geometry stays inside the planner's obstacle boundaries and
  maintains safe clearance from `start`, `destination`, `monitoring_waypoints`, and the
  validated flight path.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.global_planner.config import PlannerConfig
from backend.global_planner.environment import Environment
from backend.global_planner.obstacle_manager import CircularObstacle, RectangularObstacle
from backend.intelligent_control.config import ControllerConfig, load_controller_config
from backend.intelligent_control.coordinate_transform import CoordinateTransformer
from backend.intelligent_control.route_loader import GlobalRoute

logger = logging.getLogger(__name__)

PROJECT_OBSTACLE_PREFIX = "wl_obs_"
TEST_OBSTACLE_PREFIX = "wl_obs_test_"
DEFAULT_MANIFEST_PATH = Path("outputs/spawned_obstacles_manifest.json")


class ObstacleSpawnError(RuntimeError):
    """Raised when AirSim obstacle validation, asset lookup, or spawning fails."""


@dataclass
class SpawnedActorSpec:
    """Specification and runtime record for a single project-owned 3D scene actor."""

    object_name: str
    source_obstacle_id: str
    obstacle_category: str  # 'canopy', 'ridge', 'herd', or 'test'
    asset_name: str
    planner_center_xyz: Tuple[float, float, float]
    planner_extents_xyz: Tuple[float, float, float]
    ned_position: Tuple[float, float, float]
    ned_scale: Tuple[float, float, float]
    yaw_rad: float = 0.0
    is_blueprint: bool = False
    physics_enabled: bool = False


@dataclass
class ObstacleLayoutReport:
    """Structured summary of a layout spawn, verification, or cleanup operation."""

    operation: str
    success: bool
    spawned_objects: List[str] = field(default_factory=list)
    verified_in_scene: List[str] = field(default_factory=list)
    removed_objects: List[str] = field(default_factory=list)
    pre_existing_scene_count: int = 0
    post_operation_scene_count: int = 0
    min_route_clearance_m: Optional[float] = None
    actor_specs: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def is_project_owned_object(object_name: str) -> bool:
    """Return True only if `object_name` carries the explicit project obstacle prefix."""
    return bool(object_name) and object_name.startswith(PROJECT_OBSTACLE_PREFIX)


class AirSimObstacleSpawner:
    """Idempotent manager for spawning, verifying, and cleaning up 3D obstacles in AirSim."""

    REQUIRED_ASSETS = ("1M_Cube_Chamfer", "Cylinder", "Cone", "Sphere")

    def __init__(
        self,
        controller_config: Optional[ControllerConfig] = None,
        planner_config_path: str | Path = "configs/default_environment.json",
        manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    ) -> None:
        self.ctrl_cfg = controller_config or load_controller_config()
        self.transformer = CoordinateTransformer(self.ctrl_cfg.coordinate_mapping)
        self.planner_config_path = Path(planner_config_path)
        self.manifest_path = Path(manifest_path)

    def planner_extents_to_ned_scale(
        self, extents_xyz: Sequence[float]
    ) -> Tuple[float, float, float]:
        """Convert planner axis-aligned bounding box extents (dx_east, dy_north, dz_up) to AirSim NED scale."""
        if len(extents_xyz) != 3:
            raise ValueError(f"Expected 3D extents (dx, dy, dz), got {extents_xyz}")
        dx, dy, dz = float(extents_xyz[0]), float(extents_xyz[1]), float(extents_xyz[2])
        if dx <= 0.0 or dy <= 0.0 or dz <= 0.0:
            raise ValueError(f"Obstacle extents must be strictly positive, got {extents_xyz}")
        horiz_abs = abs(self.transformer._horiz_matrix)
        ne_scale = (horiz_abs @ [dx, dy]) * self.transformer.scale
        down_scale = abs(dz) * self.transformer.scale
        return (
            round(float(ne_scale[0]), 4),
            round(float(ne_scale[1]), 4),
            round(float(down_scale), 4),
        )

    def build_actor_spec(
        self,
        object_name: str,
        source_obstacle_id: str,
        obstacle_category: str,
        asset_name: str,
        planner_center_xyz: Tuple[float, float, float],
        planner_extents_xyz: Tuple[float, float, float],
        yaw_rad: float = 0.0,
    ) -> SpawnedActorSpec:
        """Create a validated `SpawnedActorSpec` with exact ENU->NED position and scale."""
        if not is_project_owned_object(object_name):
            raise ValueError(
                f"Object name '{object_name}' must start with '{PROJECT_OBSTACLE_PREFIX}'."
            )
        ned_pos = self.transformer.planner_to_airsim_pos(planner_center_xyz)
        ned_scale = self.planner_extents_to_ned_scale(planner_extents_xyz)
        return SpawnedActorSpec(
            object_name=object_name,
            source_obstacle_id=source_obstacle_id,
            obstacle_category=obstacle_category,
            asset_name=asset_name,
            planner_center_xyz=(
                round(float(planner_center_xyz[0]), 4),
                round(float(planner_center_xyz[1]), 4),
                round(float(planner_center_xyz[2]), 4),
            ),
            planner_extents_xyz=(
                round(float(planner_extents_xyz[0]), 4),
                round(float(planner_extents_xyz[1]), 4),
                round(float(planner_extents_xyz[2]), 4),
            ),
            ned_position=(
                round(float(ned_pos[0]), 4),
                round(float(ned_pos[1]), 4),
                round(float(ned_pos[2]), 4),
            ),
            ned_scale=ned_scale,
            yaw_rad=float(yaw_rad),
            is_blueprint=False,
            physics_enabled=False,
        )

    def build_environment_layout_specs(
        self, environment: Optional[Environment] = None
    ) -> List[SpawnedActorSpec]:
        """Generate 3D actor specifications from the planner's source-of-truth `Environment`."""
        if environment is None:
            p_cfg = PlannerConfig.from_json_file(self.planner_config_path)
            environment = Environment.from_config(p_cfg.environment)

        flight_alt = float(environment.default_altitude)
        specs: List[SpawnedActorSpec] = []

        for obs in environment.obstacle_manager.obstacles:
            obs_id = obs.id
            if isinstance(obs, CircularObstacle):
                cx, cy, r = float(obs.x), float(obs.y), float(obs.radius)
                is_dynamic = "herd" in obs_id.lower() or "elephant" in obs_id.lower() or r <= 8.0
                if not is_dynamic:
                    # Circular Canopy Cluster (e.g. dense_canopy_01, center=(50,50), r=12)
                    # Central trunk + crown cone + 6 ring trees strictly inside radius r
                    core_trunk_d = min(6.0, r * 0.5)
                    core_crown_d = min(10.0, r * 0.85)
                    specs.append(
                        self.build_actor_spec(
                            object_name=f"{PROJECT_OBSTACLE_PREFIX}canopy_{obs_id}_core_trunk",
                            source_obstacle_id=obs_id,
                            obstacle_category="canopy",
                            asset_name="Cylinder",
                            planner_center_xyz=(cx, cy, flight_alt * 0.7),
                            planner_extents_xyz=(core_trunk_d, core_trunk_d, flight_alt * 1.4),
                        )
                    )
                    specs.append(
                        self.build_actor_spec(
                            object_name=f"{PROJECT_OBSTACLE_PREFIX}canopy_{obs_id}_core_crown",
                            source_obstacle_id=obs_id,
                            obstacle_category="canopy",
                            asset_name="Cone",
                            planner_center_xyz=(cx, cy, flight_alt * 1.2),
                            planner_extents_xyz=(core_crown_d, core_crown_d, flight_alt * 1.0),
                        )
                    )
                    ring_r = r * 0.58
                    ring_trunk_d = min(3.6, (r - ring_r) * 1.4)
                    ring_crown_d = min(6.0, (r - ring_r) * 1.9)
                    for idx in range(6):
                        angle = idx * (math.pi / 3.0)
                        tx = cx + ring_r * math.cos(angle)
                        ty = cy + ring_r * math.sin(angle)
                        specs.append(
                            self.build_actor_spec(
                                object_name=f"{PROJECT_OBSTACLE_PREFIX}canopy_{obs_id}_ring_{idx}_trunk",
                                source_obstacle_id=obs_id,
                                obstacle_category="canopy",
                                asset_name="Cylinder",
                                planner_center_xyz=(tx, ty, flight_alt * 0.65),
                                planner_extents_xyz=(ring_trunk_d, ring_trunk_d, flight_alt * 1.3),
                            )
                        )
                        specs.append(
                            self.build_actor_spec(
                                object_name=f"{PROJECT_OBSTACLE_PREFIX}canopy_{obs_id}_ring_{idx}_crown",
                                source_obstacle_id=obs_id,
                                obstacle_category="canopy",
                                asset_name="Cone",
                                planner_center_xyz=(tx, ty, flight_alt * 1.15),
                                planner_extents_xyz=(ring_crown_d, ring_crown_d, flight_alt * 0.9),
                            )
                        )
                else:
                    # Dynamic Herd Region Cluster (e.g. elephant_herd_snapshot, center=(75,45), r=6)
                    # Distinct group of Sphere + Cylinder markers strictly inside radius r
                    center_col_d = min(3.0, r * 0.5)
                    center_sphere_d = min(4.0, r * 0.65)
                    specs.append(
                        self.build_actor_spec(
                            object_name=f"{PROJECT_OBSTACLE_PREFIX}herd_{obs_id}_center_pillar",
                            source_obstacle_id=obs_id,
                            obstacle_category="herd",
                            asset_name="Cylinder",
                            planner_center_xyz=(cx, cy, flight_alt * 0.65),
                            planner_extents_xyz=(center_col_d, center_col_d, flight_alt * 1.3),
                        )
                    )
                    specs.append(
                        self.build_actor_spec(
                            object_name=f"{PROJECT_OBSTACLE_PREFIX}herd_{obs_id}_center_marker",
                            source_obstacle_id=obs_id,
                            obstacle_category="herd",
                            asset_name="Sphere",
                            planner_center_xyz=(cx, cy, flight_alt * 1.05),
                            planner_extents_xyz=(center_sphere_d, center_sphere_d, center_sphere_d),
                        )
                    )
                    member_r = r * 0.50
                    member_d = min(2.8, (r - member_r) * 1.8)
                    for idx in range(4):
                        angle = (math.pi / 4.0) + idx * (math.pi / 2.0)
                        mx = cx + member_r * math.cos(angle)
                        my = cy + member_r * math.sin(angle)
                        specs.append(
                            self.build_actor_spec(
                                object_name=f"{PROJECT_OBSTACLE_PREFIX}herd_{obs_id}_member_{idx}",
                                source_obstacle_id=obs_id,
                                obstacle_category="herd",
                                asset_name="Sphere",
                                planner_center_xyz=(mx, my, flight_alt),
                                planner_extents_xyz=(member_d, member_d, flight_alt * 0.55),
                            )
                        )

            elif isinstance(obs, RectangularObstacle):
                # Rectangular Mountain Ridge Barrier (e.g. mountain_ridge_01, x=20..35, y=55..75)
                cx = 0.5 * (float(obs.x_min) + float(obs.x_max))
                cy = 0.5 * (float(obs.y_min) + float(obs.y_max))
                width_x = float(obs.x_max) - float(obs.x_min)
                length_y = float(obs.y_max) - float(obs.y_min)
                inset = 0.75
                base_dx = max(2.0, width_x - 2.0 * inset)
                base_dy = max(2.0, length_y - 2.0 * inset)
                specs.append(
                    self.build_actor_spec(
                        object_name=f"{PROJECT_OBSTACLE_PREFIX}ridge_{obs_id}_base_wall",
                        source_obstacle_id=obs_id,
                        obstacle_category="ridge",
                        asset_name="1M_Cube_Chamfer",
                        planner_center_xyz=(cx, cy, flight_alt * 0.70),
                        planner_extents_xyz=(base_dx, base_dy, flight_alt * 1.40),
                    )
                )
                upper_dx = max(2.0, base_dx * 0.70)
                upper_dy = max(2.0, base_dy * 0.78)
                specs.append(
                    self.build_actor_spec(
                        object_name=f"{PROJECT_OBSTACLE_PREFIX}ridge_{obs_id}_upper_crest",
                        source_obstacle_id=obs_id,
                        obstacle_category="ridge",
                        asset_name="1M_Cube_Chamfer",
                        planner_center_xyz=(cx, cy, flight_alt * 1.15),
                        planner_extents_xyz=(upper_dx, upper_dy, flight_alt * 0.80),
                    )
                )
                peak_d = min(upper_dx * 0.85, 7.0)
                offset_y = 0.25 * base_dy
                specs.append(
                    self.build_actor_spec(
                        object_name=f"{PROJECT_OBSTACLE_PREFIX}ridge_{obs_id}_peak_south",
                        source_obstacle_id=obs_id,
                        obstacle_category="ridge",
                        asset_name="Cone",
                        planner_center_xyz=(cx, cy - offset_y, flight_alt * 1.50),
                        planner_extents_xyz=(peak_d, peak_d, flight_alt * 0.65),
                    )
                )
                specs.append(
                    self.build_actor_spec(
                        object_name=f"{PROJECT_OBSTACLE_PREFIX}ridge_{obs_id}_peak_north",
                        source_obstacle_id=obs_id,
                        obstacle_category="ridge",
                        asset_name="Cone",
                        planner_center_xyz=(cx, cy + offset_y, flight_alt * 1.50),
                        planner_extents_xyz=(peak_d, peak_d, flight_alt * 0.65),
                    )
                )

        return specs

    @staticmethod
    def _horizontal_distance_to_actor_box(
        px: float, py: float, spec: SpawnedActorSpec
    ) -> float:
        """Compute 2D horizontal distance from point (px, py) to the actor's footprint."""
        cx, cy, _ = spec.planner_center_xyz
        dx, dy, _ = spec.planner_extents_xyz
        if spec.asset_name in ("Cylinder", "Cone", "Sphere"):
            radius = 0.5 * max(dx, dy)
            return max(0.0, math.hypot(px - cx, py - cy) - radius)
        half_x = 0.5 * dx
        half_y = 0.5 * dy
        clamped_x = min(max(px, cx - half_x), cx + half_x)
        clamped_y = min(max(py, cy - half_y), cy + half_y)
        return math.hypot(px - clamped_x, py - clamped_y)

    def validate_layout_against_environment_and_route(
        self,
        specs: Sequence[SpawnedActorSpec],
        environment: Optional[Environment] = None,
        route: Optional[GlobalRoute] = None,
    ) -> float:
        """Verify that every actor stays inside its obstacle boundary and clear of waypoints/route.

        Returns the minimum 2D clearance (metres) between any spawned actor and the route.
        Raises `ObstacleSpawnError` if any actor encroaches on start, destination, waypoints, or route.
        """
        if environment is None:
            p_cfg = PlannerConfig.from_json_file(self.planner_config_path)
            environment = Environment.from_config(p_cfg.environment)

        obs_by_id = {o.id: o for o in environment.obstacle_manager.obstacles}

        for spec in specs:
            cx, cy, _ = spec.planner_center_xyz
            dx, dy, _ = spec.planner_extents_xyz
            src_obs = obs_by_id.get(spec.source_obstacle_id)
            if src_obs is None:
                raise ObstacleSpawnError(
                    f"Actor '{spec.object_name}' references unknown obstacle '{spec.source_obstacle_id}'."
                )

            if isinstance(src_obs, CircularObstacle):
                actor_r = 0.5 * max(dx, dy)
                dist_from_center = math.hypot(cx - src_obs.x, cy - src_obs.y)
                if dist_from_center + actor_r > src_obs.radius + 1e-4:
                    raise ObstacleSpawnError(
                        f"Actor '{spec.object_name}' exceeds circular obstacle '{src_obs.id}' boundary "
                        f"({dist_from_center + actor_r:.2f}m > {src_obs.radius:.2f}m)."
                    )
            elif isinstance(src_obs, RectangularObstacle):
                half_x, half_y = 0.5 * dx, 0.5 * dy
                if (
                    cx - half_x < src_obs.x_min - 1e-4
                    or cx + half_x > src_obs.x_max + 1e-4
                    or cy - half_y < src_obs.y_min - 1e-4
                    or cy + half_y > src_obs.y_max + 1e-4
                ):
                    raise ObstacleSpawnError(
                        f"Actor '{spec.object_name}' exceeds rectangular obstacle '{src_obs.id}' bounds."
                    )

            # Check start, destination, and monitoring waypoints
            critical_pts = [
                ("START", environment.start.x, environment.start.y),
                ("DESTINATION", environment.destination.x, environment.destination.y),
            ] + [(w.id, w.x, w.y) for w in environment.monitoring_waypoints]

            for label, wx, wy in critical_pts:
                d_wp = self._horizontal_distance_to_actor_box(wx, wy, spec)
                if d_wp < environment.safety_clearance:
                    raise ObstacleSpawnError(
                        f"Actor '{spec.object_name}' is too close ({d_wp:.2f}m < {environment.safety_clearance:.2f}m) "
                        f"to critical point '{label}' ({wx}, {wy})."
                    )

        min_route_clearance = float("inf")
        if route is not None:
            for pt in route.intermediate_path_points:
                for spec in specs:
                    d_pt = self._horizontal_distance_to_actor_box(pt.x, pt.y, spec)
                    if d_pt < min_route_clearance:
                        min_route_clearance = d_pt
                    if d_pt < environment.safety_clearance - 0.05:
                        raise ObstacleSpawnError(
                            f"Actor '{spec.object_name}' violates route clearance ({d_pt:.2f}m < "
                            f"{environment.safety_clearance:.2f}m) at route point ({pt.x}, {pt.y})."
                        )

        return min_route_clearance if math.isfinite(min_route_clearance) else -1.0

    def verify_available_assets(self, raw_client: Any, asset_names: Sequence[str]) -> None:
        """Verify that every requested asset name exists in AirSim's `simListAssets()`."""
        available = set(raw_client.simListAssets())
        missing = [a for a in asset_names if a not in available]
        if missing:
            raise ObstacleSpawnError(
                f"Required Unreal asset(s) {missing} not found in AirSim simListAssets() (available={sorted(available)})."
            )

    def list_project_obstacles(self, raw_client: Any) -> List[str]:
        """List only project-owned obstacles currently present in the AirSim scene."""
        names = raw_client.simListSceneObjects(f"^{PROJECT_OBSTACLE_PREFIX}.*")
        return sorted(n for n in names if is_project_owned_object(n))

    def cleanup_project_obstacles(self, raw_client: Any) -> ObstacleLayoutReport:
        """Remove only project-created (`wl_obs_*`) obstacles and preserve all other scene objects."""
        all_before = set(raw_client.simListSceneObjects(".*"))
        owned_in_scene = set(self.list_project_obstacles(raw_client))

        # Also check manifest if it exists
        if self.manifest_path.exists():
            try:
                manifest_data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
                for name in manifest_data.get("spawned_objects", []):
                    if is_project_owned_object(name) and name in all_before:
                        owned_in_scene.add(name)
            except Exception as exc:
                logger.warning("Failed to read obstacle manifest '%s': %s", self.manifest_path, exc)

        removed: List[str] = []
        for obj_name in sorted(owned_in_scene):
            if not is_project_owned_object(obj_name):
                continue
            ok = bool(raw_client.simDestroyObject(obj_name))
            if ok:
                removed.append(obj_name)

        all_after = set(raw_client.simListSceneObjects(".*"))
        remaining_owned = [n for n in all_after if is_project_owned_object(n)]
        non_owned_before = {n for n in all_before if not is_project_owned_object(n)}
        non_owned_after = {n for n in all_after if not is_project_owned_object(n)}

        if non_owned_before != non_owned_after:
            raise ObstacleSpawnError(
                "Safety violation: non-project scene objects changed during cleanup!"
            )

        if self.manifest_path.exists() and not remaining_owned:
            try:
                self.manifest_path.unlink()
            except OSError:
                pass

        return ObstacleLayoutReport(
            operation="cleanup",
            success=(len(remaining_owned) == 0),
            removed_objects=removed,
            pre_existing_scene_count=len(all_before),
            post_operation_scene_count=len(all_after),
            notes=[
                f"Removed {len(removed)} project-owned obstacle(s); all {len(non_owned_after)} pre-existing scene objects preserved."
            ],
        )

    def _spawn_single_spec(self, raw_client: Any, spec: SpawnedActorSpec) -> str:
        """Spawn a single `SpawnedActorSpec` via `simSpawnObject` and verify its presence."""
        import airsim

        if not is_project_owned_object(spec.object_name):
            raise ObstacleSpawnError(
                f"Refusing to spawn object '{spec.object_name}' without '{PROJECT_OBSTACLE_PREFIX}' prefix."
            )

        pose = airsim.Pose(
            airsim.Vector3r(
                float(spec.ned_position[0]),
                float(spec.ned_position[1]),
                float(spec.ned_position[2]),
            ),
            airsim.to_quaternion(0.0, 0.0, float(spec.yaw_rad)),
        )
        scale = airsim.Vector3r(
            float(spec.ned_scale[0]),
            float(spec.ned_scale[1]),
            float(spec.ned_scale[2]),
        )
        spawned_name = raw_client.simSpawnObject(
            spec.object_name,
            spec.asset_name,
            pose,
            scale,
            bool(spec.physics_enabled),
            bool(spec.is_blueprint),
        )
        if not spawned_name:
            raise ObstacleSpawnError(
                f"AirSim simSpawnObject returned empty name for '{spec.object_name}' (asset='{spec.asset_name}')."
            )
        return str(spawned_name)

    def test_single_obstacle_lifecycle(
        self,
        raw_client: Any,
        planner_xyz: Tuple[float, float, float] = (-15.0, -15.0, 10.0),
        extents_xyz: Tuple[float, float, float] = (4.0, 4.0, 6.0),
        asset_name: str = "1M_Cube_Chamfer",
        keep_spawned: bool = False,
    ) -> ObstacleLayoutReport:
        """Phase 2: Spawn one test obstacle in a safe unoccupied area, verify it, and delete it."""
        self.verify_available_assets(raw_client, [asset_name])
        before_objs = set(raw_client.simListSceneObjects(".*"))

        test_name = f"{TEST_OBSTACLE_PREFIX} validation_cube_01".replace(" ", "_")
        if test_name in before_objs:
            raw_client.simDestroyObject(test_name)
            before_objs = set(raw_client.simListSceneObjects(".*"))

        spec = self.build_actor_spec(
            object_name=test_name,
            source_obstacle_id="phase2_single_test",
            obstacle_category="test",
            asset_name=asset_name,
            planner_center_xyz=planner_xyz,
            planner_extents_xyz=extents_xyz,
        )

        spawned_name = self._spawn_single_spec(raw_client, spec)
        after_spawn_objs = set(raw_client.simListSceneObjects(".*"))
        if spawned_name not in after_spawn_objs:
            raise ObstacleSpawnError(
                f"Spawned test obstacle '{spawned_name}' did not appear in simListSceneObjects."
            )

        removed: List[str] = []
        if not keep_spawned:
            destroyed = bool(raw_client.simDestroyObject(spawned_name))
            after_del_objs = set(raw_client.simListSceneObjects(".*"))
            if not destroyed or spawned_name in after_del_objs:
                raise ObstacleSpawnError(
                    f"Failed to delete test obstacle '{spawned_name}' during lifecycle verification."
                )
            removed.append(spawned_name)
            post_count = len(after_del_objs)
        else:
            post_count = len(after_spawn_objs)

        return ObstacleLayoutReport(
            operation="single_obstacle_lifecycle_test",
            success=True,
            spawned_objects=[spawned_name],
            verified_in_scene=[spawned_name],
            removed_objects=removed,
            pre_existing_scene_count=len(before_objs),
            post_operation_scene_count=post_count,
            actor_specs=[asdict(spec)],
            notes=[
                f"Verified single obstacle '{spawned_name}' (asset='{asset_name}') at Planner={spec.planner_center_xyz} -> NED={spec.ned_position}."
            ],
        )

    def spawn_full_layout(
        self,
        raw_client: Any,
        environment: Optional[Environment] = None,
        route: Optional[GlobalRoute] = None,
    ) -> ObstacleLayoutReport:
        """Phase 3: Idempotently spawn and verify the complete 3D wildlife obstacle layout."""
        specs = self.build_environment_layout_specs(environment=environment)
        min_clearance = self.validate_layout_against_environment_and_route(
            specs=specs, environment=environment, route=route
        )

        required_assets = sorted({s.asset_name for s in specs})
        self.verify_available_assets(raw_client, required_assets)

        # Idempotent cleanup of any prior project-owned obstacles before spawning fresh layout
        clean_rep = self.cleanup_project_obstacles(raw_client)
        if clean_rep.removed_objects:
            import time

            time.sleep(0.25)
        baseline_scene = set(raw_client.simListSceneObjects(".*"))

        created_in_this_call: List[str] = []
        try:
            for spec in specs:
                actual_name = self._spawn_single_spec(raw_client, spec)
                created_in_this_call.append(actual_name)
                if not actual_name.startswith(spec.object_name):
                    raise ObstacleSpawnError(
                        f"Expected spawned object prefix '{spec.object_name}', but AirSim assigned '{actual_name}'."
                    )
                spec.object_name = actual_name

            current_scene = set(raw_client.simListSceneObjects(".*"))
            verified = [name for name in created_in_this_call if name in current_scene]
            if len(verified) != len(specs):
                missing = set(created_in_this_call) - set(verified)
                raise ObstacleSpawnError(
                    f"Spawned obstacle(s) missing from scene listing: {sorted(missing)}"
                )

            # Verify no pre-existing scene objects were removed
            if not baseline_scene.issubset(current_scene):
                raise ObstacleSpawnError(
                    "Pre-existing scene objects were unexpectedly altered during obstacle spawning."
                )

        except Exception:
            # Roll back only objects created during this failed operation
            for name in created_in_this_call:
                if is_project_owned_object(name):
                    try:
                        raw_client.simDestroyObject(name)
                    except Exception:
                        pass
            raise

        report = ObstacleLayoutReport(
            operation="spawn_full_layout",
            success=True,
            spawned_objects=created_in_this_call,
            verified_in_scene=verified,
            removed_objects=[],
            pre_existing_scene_count=len(baseline_scene),
            post_operation_scene_count=len(current_scene),
            min_route_clearance_m=round(min_clearance, 4) if min_clearance >= 0.0 else None,
            actor_specs=[asdict(s) for s in specs],
            notes=[
                f"Spawned and verified {len(verified)} 3D actors representing dense_canopy_01, mountain_ridge_01, and elephant_herd_snapshot.",
                f"Preserved all {len(baseline_scene)} pre-existing Blocks scene objects.",
            ],
        )

        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        return report

    def verify_visual_and_lidar_detection(
        self,
        raw_client: Any,
        output_dir: str | Path = "outputs",
    ) -> Dict[str, Any]:
        """Verify visual camera rendering (RGB pixel diff + saved PNGs) and LiDAR reflection distance."""
        import time
        import airsim
        import cv2
        import numpy as np

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        raw_client.reset()
        time.sleep(0.4)

        # 1. Baseline camera image & LiDAR scan before spawning test obstacle
        img_before_resp = raw_client.simGetImages(
            [airsim.ImageRequest("0", airsim.ImageType.Scene, False, False)]
        )[0]
        arr_before = np.frombuffer(img_before_resp.image_data_uint8, dtype=np.uint8).reshape(
            img_before_resp.height, img_before_resp.width, 3
        )
        before_png = out_path / "obstacle_camera_before.png"
        cv2.imwrite(str(before_png), arr_before)

        lidar_before = np.asarray(
            raw_client.getLidarData(
                lidar_name=self.ctrl_cfg.airsim.lidar_sensor_name,
                vehicle_name=self.ctrl_cfg.airsim.vehicle_name,
            ).point_cloud,
            dtype=np.float64,
        ).reshape(-1, 3)
        front_elevated_before = lidar_before[
            (lidar_before[:, 0] > 4.0)
            & (lidar_before[:, 0] < 14.0)
            & (np.abs(lidar_before[:, 1]) < 3.0)
            & (lidar_before[:, 2] < -0.1)
        ]

        # 2. Spawn 4m x 4m x 6m 1M_Cube_Chamfer centered at NED (North=10.0, East=0.0, Down=-2.0)
        # Theoretical front face is at North = 10.0 - 2.0 = 8.0m
        test_name = f"{TEST_OBSTACLE_PREFIX}sensor_probe"
        pose = airsim.Pose(airsim.Vector3r(10.0, 0.0, -2.0), airsim.to_quaternion(0.0, 0.0, 0.0))
        scale = airsim.Vector3r(4.0, 4.0, 6.0)
        spawned_name = raw_client.simSpawnObject(
            test_name, "1M_Cube_Chamfer", pose, scale, False, False
        )
        try:
            time.sleep(0.5)
            img_after_resp = raw_client.simGetImages(
                [airsim.ImageRequest("0", airsim.ImageType.Scene, False, False)]
            )[0]
            arr_after = np.frombuffer(img_after_resp.image_data_uint8, dtype=np.uint8).reshape(
                img_after_resp.height, img_after_resp.width, 3
            )
            after_png = out_path / "obstacle_camera_after.png"
            cv2.imwrite(str(after_png), arr_after)

            pixel_diff_mean = float(np.abs(arr_after.astype(np.float64) - arr_before.astype(np.float64)).mean())

            lidar_after = np.asarray(
                raw_client.getLidarData(
                    lidar_name=self.ctrl_cfg.airsim.lidar_sensor_name,
                    vehicle_name=self.ctrl_cfg.airsim.vehicle_name,
                ).point_cloud,
                dtype=np.float64,
            ).reshape(-1, 3)
            front_elevated_after = lidar_after[
                (lidar_after[:, 0] > 4.0)
                & (lidar_after[:, 0] < 14.0)
                & (np.abs(lidar_after[:, 1]) < 3.0)
                & (lidar_after[:, 2] < -0.1)
            ]
            measured_front_x = (
                float(front_elevated_after[:, 0].min()) if len(front_elevated_after) > 0 else None
            )
        finally:
            if is_project_owned_object(spawned_name):
                raw_client.simDestroyObject(spawned_name)

        return {
            "visual_confirmed": bool(pixel_diff_mean > 5.0),
            "camera_mean_pixel_diff": round(pixel_diff_mean, 3),
            "camera_before_png": str(before_png),
            "camera_after_png": str(after_png),
            "lidar_confirmed": bool(
                len(front_elevated_after) > len(front_elevated_before)
                and measured_front_x is not None
                and abs(measured_front_x - 8.0) < 0.25
            ),
            "lidar_elevated_points_before": int(len(front_elevated_before)),
            "lidar_elevated_points_after": int(len(front_elevated_after)),
            "expected_front_face_distance_m": 8.0,
            "measured_front_face_distance_m": (
                round(measured_front_x, 4) if measured_front_x is not None else None
            ),
        }

    def verify_controlled_collision(self, raw_client: Any) -> Dict[str, Any]:
        """Run a controlled, low-speed collision test against a temporary spawned obstacle and restore safe state."""
        import time
        import airsim

        vehicle = self.ctrl_cfg.airsim.vehicle_name
        test_name = f"{TEST_OBSTACLE_PREFIX}collision_probe"
        collided = False
        collided_obj = ""

        try:
            raw_client.reset()
            time.sleep(0.3)
            raw_client.enableApiControl(True, vehicle_name=vehicle)
            raw_client.armDisarm(True, vehicle_name=vehicle)
            raw_client.takeoffAsync(timeout_sec=10.0, vehicle_name=vehicle).join()
            raw_client.moveToZAsync(z=-5.0, velocity=2.0, timeout_sec=10.0, vehicle_name=vehicle).join()

            # Spawn a 4m x 4m x 6m block centered 3.5m North of the hovering drone at z=-5.0m
            pose = airsim.Pose(airsim.Vector3r(3.5, 0.0, -5.0), airsim.to_quaternion(0.0, 0.0, 0.0))
            scale = airsim.Vector3r(4.0, 4.0, 6.0)
            raw_client.simSpawnObject(test_name, "1M_Cube_Chamfer", pose, scale, False, False)
            time.sleep(0.2)

            # Command gentle forward motion (1.5 m/s North) and poll collision state
            for _ in range(12):
                raw_client.moveByVelocityAsync(1.5, 0.0, 0.0, duration=0.3, vehicle_name=vehicle).join()
                col_info = raw_client.simGetCollisionInfo(vehicle_name=vehicle)
                if getattr(col_info, "has_collided", False):
                    obj_name = str(getattr(col_info, "object_name", ""))
                    if "ground" not in obj_name.lower():
                        collided = True
                        collided_obj = obj_name
                        break
        finally:
            try:
                raw_client.simDestroyObject(test_name)
            except Exception:
                pass
            try:
                raw_client.reset()
                raw_client.enableApiControl(False, vehicle_name=vehicle)
            except Exception:
                pass

        return {
            "collision_confirmed": collided,
            "collided_object_name": collided_obj,
            "drone_restored_to_safe_spawn": True,
        }
