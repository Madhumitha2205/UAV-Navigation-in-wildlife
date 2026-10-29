"""Unit tests for Adaptive Fuzzy Logic (AFL) safety layer membership functions and rules."""

import math
import numpy as np

from backend.intelligent_control.airsim_sensors import ObstacleObservation
from backend.intelligent_control.config import SafetyConfig, VehicleLimitsConfig
from backend.intelligent_control.fuzzy_safety import AdaptiveFuzzySafetyLayer


def test_fuzzy_distance_and_closing_speed_memberships():
    safety = AdaptiveFuzzySafetyLayer(
        safety_config=SafetyConfig(safe_distance_m=6.0, critical_distance_m=2.5),
        limits_config=VehicleLimitsConfig(max_velocity_xy_mps=5.0, max_velocity_z_mps=2.0),
    )

    # At critical distance (<= 2.5m), critical membership is 1.0
    m_crit = safety.compute_distance_memberships(2.0)
    assert np.isclose(m_crit["critical"], 1.0)
    assert np.isclose(m_crit["safe"], 0.0)

    # At midpoint (4.25m), near membership is 1.0
    m_near = safety.compute_distance_memberships(4.25)
    assert np.isclose(m_near["near"], 1.0)

    # Beyond safe distance (>= 6.0m), safe membership is 1.0
    m_safe = safety.compute_distance_memberships(8.0)
    assert np.isclose(m_safe["safe"], 1.0)
    assert np.isclose(m_safe["critical"], 0.0)


def test_clear_surroundings_passes_action_through():
    safety = AdaptiveFuzzySafetyLayer()
    obs = ObstacleObservation(
        sensor_mode="LIDAR",
        is_valid=True,
        has_collided=False,
        closest_distance_m=15.0,
        repulsion_unit_xyz=(-1.0, 0.0, 0.0),
        obstacle_rel_xyz=(15.0, 0.0, 0.0),
        closing_speed_mps=1.0,
    )
    res = safety.filter_action(td3_action_xyz=(3.5, 1.0, 0.0), uav_vel_xyz=(3.0, 1.0, 0.0), obstacle_obs=obs)
    assert res.intervened is False
    assert res.danger_level < 0.15
    assert np.allclose(res.final_action, (3.5, 1.0, 0.0))


def test_critical_obstacle_proximity_intervenes_and_repels():
    safety = AdaptiveFuzzySafetyLayer()
    # Obstacle is directly ahead at +X (distance 1.8m < 2.5m critical), repulsion points -X
    obs = ObstacleObservation(
        sensor_mode="LIDAR",
        is_valid=True,
        has_collided=False,
        closest_distance_m=1.8,
        repulsion_unit_xyz=(-1.0, 0.0, 0.0),
        obstacle_rel_xyz=(1.8, 0.0, 0.0),
        closing_speed_mps=4.0,
    )
    # TD3 proposes flying straight into obstacle (+4.5, 0, 0)
    res = safety.filter_action(td3_action_xyz=(4.5, 0.0, 0.0), uav_vel_xyz=(4.0, 0.0, 0.0), obstacle_obs=obs)
    assert res.intervened is True
    assert res.danger_level >= 0.80
    # Final X velocity must be strongly reduced / reversed away from the +X obstacle
    assert res.final_action[0] < 0.0
    assert "CRITICAL" in res.reason


def test_invalid_sensor_input_triggers_cautious_fallback():
    safety = AdaptiveFuzzySafetyLayer()
    invalid_obs = ObstacleObservation(
        sensor_mode="UNAVAILABLE",
        is_valid=False,
        has_collided=False,
        closest_distance_m=float("nan"),
        repulsion_unit_xyz=(0.0, 0.0, 0.0),
        obstacle_rel_xyz=(0.0, 0.0, 0.0),
        closing_speed_mps=0.0,
    )
    res = safety.filter_action(td3_action_xyz=(4.0, 2.0, 0.0), uav_vel_xyz=(2.0, 1.0, 0.0), obstacle_obs=invalid_obs)
    assert res.intervened is True
    assert math.isnan(res.closest_obstacle_distance_m)
    assert np.allclose(res.final_action, (2.0, 1.0, 0.0))


def test_action_clipping_bounds():
    safety = AdaptiveFuzzySafetyLayer()
    obs = ObstacleObservation(
        sensor_mode="LIDAR",
        is_valid=True,
        has_collided=False,
        closest_distance_m=20.0,
        repulsion_unit_xyz=(-1.0, 0.0, 0.0),
        obstacle_rel_xyz=(20.0, 0.0, 0.0),
        closing_speed_mps=0.0,
    )
    res = safety.filter_action(td3_action_xyz=(12.0, -9.0, 5.0), uav_vel_xyz=(0.0, 0.0, 0.0), obstacle_obs=obs)
    assert np.allclose(res.final_action, (5.0, -5.0, 2.0))
