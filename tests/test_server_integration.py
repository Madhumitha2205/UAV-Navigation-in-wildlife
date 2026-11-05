"""Integration tests for the unified UAV Ground Control Station backend server."""

from pathlib import Path
import json
import pytest
from backend.server import app, manager
from backend.intelligent_control.coordinate_transform import CoordinateTransformer


@pytest.fixture
def client():
    app.config["TESTING"] = True
    cr_path = Path("outputs/controller_route.json")
    pr_path = Path("outputs/planned_route.json")
    cr_bytes = cr_path.read_bytes() if cr_path.exists() else None
    pr_bytes = pr_path.read_bytes() if pr_path.exists() else None

    with app.test_client() as client:
        yield client

    if cr_bytes is not None:
        cr_path.write_bytes(cr_bytes)
    if pr_bytes is not None:
        pr_path.write_bytes(pr_bytes)


def test_simulation_status_endpoint(client):
    res = client.get("/api/simulation/status")
    assert res.status_code == 200
    data = res.get_json()
    assert "simulator_connected" in data
    assert "flight_state" in data
    assert "uav_armed" in data


def test_server_uses_configured_airsim_coordinate_datum():
    transformer = CoordinateTransformer(manager.controller_cfg.coordinate_mapping)

    assert transformer.planner_to_airsim_pos((0.0, 0.0, 10.0)) == (0.0, 0.0, -28.0)


def test_live_mission_requires_a_reachable_airsim(client, monkeypatch, tmp_path):
    (tmp_path / "controller_route.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("backend.server.OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr("backend.intelligent_control.route_loader.load_global_route", lambda path: object())
    monkeypatch.setattr(manager, "_test_airsim_connection", lambda silent=False: False)
    manager.flight_state = "IDLE"

    response = client.post(
        "/api/mission/start",
        json={"mission_id": "test_live_mission", "execution_backend": "airsim"},
    )

    assert response.status_code == 503
    assert response.get_json()["success"] is False


def test_planner_plan_with_india_gps_coordinates(client):
    """Verify route planning using real geographical coordinates in India (Kaziranga Sanctuary)."""
    payload = {
        "start_position": {"lat": 26.5775, "lon": 93.1711, "alt": 10.0, "x": 5.0, "y": 5.0, "z": 10.0},
        "destination": {"lat": 26.6500, "lon": 93.2500, "alt": 10.0, "x": 95.0, "y": 95.0, "z": 10.0},
        "monitoring_waypoints": [
            {"id": "wp_alpha", "zone_name": "Waterhole Alpha", "lat": 26.5890, "lon": 93.1820, "alt": 10.0, "priority": 1},
            {"id": "wp_bravo", "zone_name": "Grassland Bravo", "lat": 26.6150, "lon": 93.2200, "alt": 10.0, "priority": 2},
        ],
        "obstacles": [
            {"id": "obs_canopy", "type": "circle", "lat": 26.6000, "lon": 93.2000, "radius": 8.0},
        ],
        "planning_params": {
            "population_size": 40,
            "max_generations": 30,
            "crossover_probability": 0.8,
            "mutation_probability": 0.02,
            "two_opt_frequency": 5,
            "two_opt_population_pct": 0.2,
            "random_seed": 42,
        },
    }

    res = client.post("/api/planner/plan", data=json.dumps(payload), content_type="application/json")
    assert res.status_code == 200
    route = res.get_json()

    assert route["status"] if "status" in route else route["validation"]["is_valid"]
    assert "start_position" in route
    assert "lat" in route["start_position"]
    assert "lon" in route["start_position"]
    assert len(route["intermediate_path_points"]) > 0
    # Confirm path points have GPS lat and lon
    first_pt = route["intermediate_path_points"][0]
    assert "lat" in first_pt
    assert "lon" in first_pt
    assert 26.0 < first_pt["lat"] < 27.0
    assert 93.0 < first_pt["lon"] < 94.0

    # Confirm metrics
    assert route["path_metrics"]["planned_path_length_m"] > 0
    assert route["path_metrics"]["monitoring_coverage_pct"] == 100.0


def test_mission_history_and_feedback(client):
    """Verify mission history retrieval and user satisfaction evaluation."""
    # 1. Get initial history
    res_hist = client.get("/api/mission/history")
    assert res_hist.status_code == 200
    hist = res_hist.get_json()
    assert isinstance(hist, list)

    # 2. Test Feedback on dummy mission
    dummy_mission_id = "test_mission_9999"
    from backend.server import _save_mission_history_record
    _save_mission_history_record({
        "mission_id": dummy_mission_id,
        "timestamp": "2026-11-04 19:00:00",
        "nav_mode": "TD3_WITH_FUZZY_SAFETY",
        "success": True,
        "planned_distance_m": 294.85,
        "actual_distance_m": 282.08,
        "planned_time_sec": 84.2,
        "actual_time_sec": 81.1,
        "avoidance_interventions": 12,
        "collision_count": 0,
        "satisfaction_status": "PENDING_FEEDBACK",
        "optimization_attempts": 1,
    })

    # Test 'Not Satisfied'
    res_fb_not_sat = client.post(
        "/api/mission/feedback",
        data=json.dumps({"mission_id": dummy_mission_id, "satisfied": False, "comment": "Too many interventions"}),
        content_type="application/json",
    )
    assert res_fb_not_sat.status_code == 200
    data_fb = res_fb_not_sat.get_json()
    assert data_fb["satisfied"] is False
    assert len(data_fb["diagnostics"]) > 0
    assert data_fb["can_reoptimize"] is True

    # Test 'Satisfied'
    res_fb_sat = client.post(
        "/api/mission/feedback",
        data=json.dumps({"mission_id": dummy_mission_id, "satisfied": True}),
        content_type="application/json",
    )
    assert res_fb_sat.status_code == 200
    data_sat = res_fb_sat.get_json()
    assert data_sat["satisfied"] is True
