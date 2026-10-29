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
