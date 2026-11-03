"""Unit tests for Global Route JSON loading and schema validation."""

import json
from pathlib import Path
import pytest

from backend.intelligent_control.route_loader import (
    GlobalRoute,
    RouteValidationError,
    load_global_route,
)


def test_load_valid_sample_route():
    route = load_global_route("configs/sample_global_route.json")
    assert isinstance(route, GlobalRoute)
    assert route.mission_id == "wildlife_monitoring_corridor_01"
    assert route.start_position.to_tuple() == (0.0, 0.0, 15.0)
    assert route.destination.to_tuple() == (60.0, 50.0, 15.0)
    assert len(route.monitoring_waypoints) == 3
    assert len(route.intermediate_path_points) == 9
    assert len(route.static_obstacles) == 3


def test_reject_missing_required_fields(tmp_path: Path):
    bad_file = tmp_path / "missing_fields.json"
    bad_file.write_text(json.dumps({"start_position": {"x": 0, "y": 0, "z": 10}}), encoding="utf-8")
    with pytest.raises(RouteValidationError, match="missing required top-level fields"):
        load_global_route(bad_file)


def test_reject_unsuccessful_planning_validation(tmp_path: Path):
    sample = json.loads(Path("configs/sample_global_route.json").read_text(encoding="utf-8"))
    sample["validation"]["is_valid"] = False
    sample["validation"]["status"] = "FAILED_NO_PATH"
    bad_file = tmp_path / "invalid_plan.json"
    bad_file.write_text(json.dumps(sample), encoding="utf-8")
    with pytest.raises(RouteValidationError, match="Global planner marked route as invalid"):
        load_global_route(bad_file)


def test_reject_malformed_json_and_missing_coords(tmp_path: Path):
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not_valid_json", encoding="utf-8")
    with pytest.raises(RouteValidationError, match="Malformed JSON"):
        load_global_route(malformed)

    sample = json.loads(Path("configs/sample_global_route.json").read_text(encoding="utf-8"))
    del sample["destination"]["z"]
    missing_z = tmp_path / "missing_z.json"
    missing_z.write_text(json.dumps(sample), encoding="utf-8")
    with pytest.raises(RouteValidationError, match="missing required coordinate 'z'"):
        load_global_route(missing_z)


def test_planned_route_to_controller_route_conversion_and_round_trip(tmp_path: Path):
    """Verify automatic conversion from planned_route.json to controller_route.json preserves all waypoints, path points, and obstacles."""
    from backend.global_planner.config import PlannerConfig
    from backend.global_planner.planner_service import GlobalPlannerService
    from backend.intelligent_control.route_loader import convert_planned_route_file

    cfg = PlannerConfig.from_json_file("configs/default_environment.json")
    cfg.export_plots = False
    service = GlobalPlannerService(cfg)
    env = service.generate_environment(cfg.environment)
    planned = service.plan_route(env, cfg)

    planned_path = tmp_path / "planned_route.json"
    ctrl_path = tmp_path / "controller_route.json"
    service.export_route(planned, planned_path)
    service.export_controller_route(planned, ctrl_path, environment=env)

    loaded_ctrl = load_global_route(ctrl_path)
    assert len(loaded_ctrl.monitoring_waypoints) == 6
    assert [w.waypoint_id for w in loaded_ctrl.monitoring_waypoints] == [
        w["id"] for w in planned.ordered_monitoring_waypoints
    ]
    assert len(loaded_ctrl.intermediate_path_points) == len(planned.path_points)
    assert abs(loaded_ctrl.path_metrics["planned_path_length_m"] - planned.metrics.path_length) < 1e-3
    assert len(loaded_ctrl.static_obstacles) == len(env.obstacle_manager.obstacles)

    # Also verify convert_planned_route_file directly on planned_route.json
    converted_path = tmp_path / "converted_from_planned.json"
    loaded_converted = convert_planned_route_file(planned_path, converted_path)
    assert len(loaded_converted.monitoring_waypoints) == 6
    assert len(loaded_converted.intermediate_path_points) == len(planned.path_points)


def test_reject_missing_file_and_endpoint_mismatch(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Global route file not found"):
        load_global_route(tmp_path / "nonexistent_route.json")

    sample = json.loads(Path("configs/sample_global_route.json").read_text(encoding="utf-8"))
    # Corrupt final intermediate path point so it no longer matches destination
    sample["intermediate_path_points"][-1]["x"] = 0.0
    sample["intermediate_path_points"][-1]["y"] = 0.0
    bad_dest = tmp_path / "bad_dest_endpoint.json"
    bad_dest.write_text(json.dumps(sample), encoding="utf-8")
    with pytest.raises(RouteValidationError, match="does not match destination"):
        load_global_route(bad_dest)
