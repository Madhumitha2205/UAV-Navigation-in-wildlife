"""Unit tests for AirSim 3D obstacle visualization, coordinate conversion, safety validation, and cleanup."""

from pathlib import Path
from typing import Dict, List, Set, Tuple
import numpy as np
import pytest

from backend.global_planner.config import PlannerConfig
from backend.global_planner.environment import Environment
from backend.intelligent_control.config import ControllerConfig
from backend.intelligent_control.obstacle_spawner import (
    PROJECT_OBSTACLE_PREFIX,
    AirSimObstacleSpawner,
    ObstacleSpawnError,
    is_project_owned_object,
)
from backend.intelligent_control.route_loader import load_global_route


class MockAirSimRawClient:
    """In-memory mock of AirSim MultirotorClient scene object APIs."""

    def __init__(self, fail_on_object: str | None = None) -> None:
        self.assets: List[str] = ["1M_Cube_Chamfer", "Cylinder", "Cone", "Sphere", "Cube"]
        self.pre_existing: Set[str] = {
            "SimpleFlight",
            "Ground_5",
            "TemplateCube_Rounded_149",
            "LightSource_0",
        }
        self.scene_objects: Dict[str, Tuple[str, object, object]] = {
            name: ("PreExisting", None, None) for name in self.pre_existing
        }
        self.fail_on_object = fail_on_object
        self.destroyed_history: List[str] = []

    def simListAssets(self) -> List[str]:
        return list(self.assets)

    def simListSceneObjects(self, name_regex: str = ".*") -> List[str]:
        import re

        pattern = re.compile(name_regex)
        return sorted(name for name in self.scene_objects if pattern.match(name))

    def simSpawnObject(
        self,
        object_name: str,
        asset_name: str,
        pose: object,
        scale: object,
        physics_enabled: bool = False,
        is_blueprint: bool = False,
    ) -> str:
        if self.fail_on_object and object_name == self.fail_on_object:
            return ""
        self.scene_objects[object_name] = (asset_name, pose, scale)
        return object_name

    def simDestroyObject(self, object_name: str) -> bool:
        if object_name in self.scene_objects:
            del self.scene_objects[object_name]
            self.destroyed_history.append(object_name)
            return True
        return False


def test_enu_to_ned_obstacle_pose_and_rectangular_scale(tmp_path: Path):
    """Verify ENU (X=East, Y=North, Z=Up) to NED (North=Y, East=X, Down=-Z+origin_d) conversion."""
    ctrl_cfg = ControllerConfig()
    ctrl_cfg.coordinate_mapping.origin_ned = [0.0, 0.0, -18.0]
    spawner = AirSimObstacleSpawner(
        controller_config=ctrl_cfg,
        manifest_path=tmp_path / "manifest.json",
    )

    # Ridge centered at East=27.5, North=65.0, Alt=10.0 with East width=14.0, North length=19.0, height=12.0
    spec = spawner.build_actor_spec(
        object_name=f"{PROJECT_OBSTACLE_PREFIX}ridge_test",
        source_obstacle_id="mountain_ridge_01",
        obstacle_category="ridge",
        asset_name="1M_Cube_Chamfer",
        planner_center_xyz=(27.5, 65.0, 10.0),
        planner_extents_xyz=(14.0, 19.0, 12.0),
    )
    # NED position: North=65.0, East=27.5, Down=-10.0 + (-18.0) = -28.0
    assert np.allclose(spec.ned_position, (65.0, 27.5, -28.0))
    # NED scale: North scale=19.0 (dy_north), East scale=14.0 (dx_east), Down scale=12.0
    assert np.allclose(spec.ned_scale, (19.0, 14.0, 12.0))


def test_ownership_prefix_enforced(tmp_path: Path):
    spawner = AirSimObstacleSpawner(manifest_path=tmp_path / "manifest.json")
    assert is_project_owned_object("wl_obs_canopy_01") is True
    assert is_project_owned_object("TemplateCube_Rounded_149") is False

    with pytest.raises(ValueError, match="must start with 'wl_obs_'"):
        spawner.build_actor_spec(
            object_name="TemplateCube_Rounded_149",
            source_obstacle_id="dense_canopy_01",
            obstacle_category="canopy",
            asset_name="Cylinder",
            planner_center_xyz=(50.0, 50.0, 10.0),
            planner_extents_xyz=(4.0, 4.0, 10.0),
        )


def test_layout_generation_and_boundary_route_validation(tmp_path: Path):
    """Verify generated layout covers canopy, ridge, and herd while staying strictly inside boundaries and clear of route."""
    spawner = AirSimObstacleSpawner(manifest_path=tmp_path / "manifest.json")
    p_cfg = PlannerConfig.from_json_file("configs/default_environment.json")
    env = Environment.from_config(p_cfg.environment)
    specs = spawner.build_environment_layout_specs(env)

    categories = {s.obstacle_category for s in specs}
    assert categories == {"canopy", "ridge", "herd"}
    assert all(is_project_owned_object(s.object_name) for s in specs)
    assert len({s.object_name for s in specs}) == len(specs)

    route = load_global_route("outputs/controller_route.json")
    min_clearance = spawner.validate_layout_against_environment_and_route(
        specs=specs, environment=env, route=route
    )
    assert min_clearance >= env.safety_clearance

    # Verify that oversized actor protruding past obstacle boundary is rejected
    bad_spec = spawner.build_actor_spec(
        object_name=f"{PROJECT_OBSTACLE_PREFIX}oversized_canopy",
        source_obstacle_id="dense_canopy_01",
        obstacle_category="canopy",
        asset_name="Cylinder",
        planner_center_xyz=(50.0, 50.0, 10.0),
        planner_extents_xyz=(30.0, 30.0, 10.0),  # radius 15m > 12m!
    )
    with pytest.raises(ObstacleSpawnError, match="exceeds circular obstacle"):
        spawner.validate_layout_against_environment_and_route([bad_spec], environment=env)


def test_idempotent_spawn_rollback_and_safe_cleanup(tmp_path: Path):
    """Verify repeated execution is idempotent, rollback cleans partial spawns, and pre-existing objects are never touched."""
    spawner = AirSimObstacleSpawner(manifest_path=tmp_path / "manifest.json")
    mock_client = MockAirSimRawClient()

    # 1. Single obstacle lifecycle test
    single_rep = spawner.test_single_obstacle_lifecycle(mock_client)
    assert single_rep.success is True
    assert set(mock_client.scene_objects.keys()) == mock_client.pre_existing

    # 2. First full layout spawn
    rep1 = spawner.spawn_full_layout(mock_client)
    assert rep1.success is True
    assert len(rep1.spawned_objects) == 24
    assert (tmp_path / "manifest.json").exists()

    # 3. Repeated full layout spawn (idempotent: must not accumulate duplicate objects)
    rep2 = spawner.spawn_full_layout(mock_client)
    assert rep2.success is True
    assert len(spawner.list_project_obstacles(mock_client)) == len(rep1.spawned_objects)
    assert mock_client.pre_existing.issubset(set(mock_client.scene_objects.keys()))

    # 4. Cleanup removes ONLY project-owned objects
    clean_rep = spawner.cleanup_project_obstacles(mock_client)
    assert clean_rep.success is True
    assert len(clean_rep.removed_objects) == len(rep1.spawned_objects)
    assert set(mock_client.scene_objects.keys()) == mock_client.pre_existing
    assert not any(not is_project_owned_object(n) for n in mock_client.destroyed_history)

    # 5. Rollback on mid-layout spawn failure cleans up partial objects
    specs = spawner.build_environment_layout_specs()
    failing_client = MockAirSimRawClient(fail_on_object=specs[5].object_name)
    with pytest.raises(ObstacleSpawnError, match="returned empty name"):
        spawner.spawn_full_layout(failing_client)
    assert set(failing_client.scene_objects.keys()) == failing_client.pre_existing
