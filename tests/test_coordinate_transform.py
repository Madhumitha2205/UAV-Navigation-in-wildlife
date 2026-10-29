"""Unit tests for CoordinateTransformer (Planner ENU/Alt-Up <-> AirSim NED)."""

import numpy as np
import pytest

from backend.intelligent_control.config import CoordinateMappingConfig
from backend.intelligent_control.coordinate_transform import CoordinateTransformer
from backend.intelligent_control.route_loader import load_global_route


def test_planner_to_airsim_ned_mapping():
    transformer = CoordinateTransformer()
    # Planner X=20 (East), Y=15 (North), Z=16 (+Up) -> AirSim North=15, East=20, Down=-16
    n, e, d = transformer.planner_to_airsim_pos((20.0, 15.0, 16.0))
    assert np.isclose(n, 15.0)
    assert np.isclose(e, 20.0)
    assert np.isclose(d, -16.0)


def test_position_and_velocity_round_trip():
    cfg = CoordinateMappingConfig(
        origin_planner=[5.0, -10.0, 2.0],
        origin_ned=[1.0, 2.0, -3.0],
        scale=1.0,
    )
    transformer = CoordinateTransformer(cfg)
    pts = [
        (0.0, 0.0, 15.0),
        (25.5, -14.2, 22.8),
        (-10.0, 42.0, 5.0),
    ]
    for p in pts:
        ned = transformer.planner_to_airsim_pos(p)
        recovered = transformer.airsim_to_planner_pos(ned)
        assert np.allclose(p, recovered, atol=1e-7)

    vels = [(3.5, -2.0, 1.2), (-4.0, 0.5, -0.8)]
    for v in vels:
        v_ned = transformer.planner_to_airsim_vel(v)
        v_rec = transformer.airsim_to_planner_vel(v_ned)
        assert np.allclose(v, v_rec, atol=1e-7)


def test_route_and_obstacle_batch_conversion():
    route = load_global_route("configs/sample_global_route.json")
    transformer = CoordinateTransformer()
    ned_wps = transformer.convert_route_points_to_airsim(route.monitoring_waypoints)
    assert len(ned_wps) == len(route.monitoring_waypoints)
    # First waypoint (20, 15, 16) -> (15, 20, -16)
    assert np.allclose(ned_wps[0], (15.0, 20.0, -16.0))

    obs_ned = transformer.convert_obstacles_to_airsim(route.static_obstacles)
    assert len(obs_ned) == len(route.static_obstacles)
    assert obs_ned[0][2] < 0.0  # Down coordinate is negative for positive altitude


def test_singular_matrix_rejected():
    bad_cfg = CoordinateMappingConfig(x_to_north=0.0, y_to_north=0.0, x_to_east=1.0, y_to_east=0.0)
    with pytest.raises(ValueError, match="singular"):
        CoordinateTransformer(bad_cfg)
