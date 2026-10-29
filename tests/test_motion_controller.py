"""Unit tests for MotionController waypoint advancement, untrained policy guard, and AirSim optional skip."""

import socket
import numpy as np
import pytest

from backend.intelligent_control.airsim_client import AirSimUAVClient
from backend.intelligent_control.airsim_sensors import ObstacleObservation
from backend.intelligent_control.config import ControllerConfig, SafetyConfig
from backend.intelligent_control.motion_controller import MotionController
from backend.intelligent_control.route_loader import RoutePoint
from backend.intelligent_control.td3_agent import TD3Agent


def _clear_obs() -> ObstacleObservation:
    return ObstacleObservation(
        sensor_mode="LIDAR",
        is_valid=True,
        has_collided=False,
        closest_distance_m=25.0,
        repulsion_unit_xyz=(0.0, 0.0, 0.0),
        obstacle_rel_xyz=(25.0, 0.0, 0.0),
        closing_speed_mps=0.0,
    )


def test_untrained_td3_policy_rejected():
    ctrl_cfg = ControllerConfig()
    safety_cfg = SafetyConfig()
    untrained_agent = TD3Agent(td3_config=ctrl_cfg.td3, limits_config=ctrl_cfg.vehicle_limits)
    wps = [RoutePoint(x=10.0, y=0.0, z=15.0, is_monitoring=True, waypoint_id="WP_1")]

    mc = MotionController(
        controller_config=ctrl_cfg,
        safety_config=safety_cfg,
        route_points=wps,
        td3_agent=untrained_agent,
        nav_mode="TD3_WITH_FUZZY_SAFETY",
    )
    with pytest.raises(RuntimeError, match="Refusing to execute an untrained TD3 actor policy"):
        mc.compute_control_step((0.0, 0.0, 15.0), (0.0, 0.0, 0.0), _clear_obs())


def test_waypoint_advancement_and_mission_completion():
    ctrl_cfg = ControllerConfig()
    safety_cfg = SafetyConfig()
    agent = TD3Agent(td3_config=ctrl_cfg.td3, limits_config=ctrl_cfg.vehicle_limits)
    agent.is_trained = True

    wps = [
        RoutePoint(x=5.0, y=0.0, z=15.0, is_monitoring=True, waypoint_id="WP_1"),
        RoutePoint(x=10.0, y=0.0, z=15.0, is_monitoring=False, waypoint_id="DEST"),
    ]
    mc = MotionController(
        controller_config=ctrl_cfg,
        safety_config=safety_cfg,
        route_points=wps,
        td3_agent=agent,
        nav_mode="TD3_WITH_FUZZY_SAFETY",
    )

    # At start (0,0,15), targets WP_1
    out1 = mc.compute_control_step((0.0, 0.0, 15.0), (0.0, 0.0, 0.0), _clear_obs())
    assert out1.active_waypoint_id == "WP_1"
    assert not out1.mission_completed

    # Within tolerance of WP_1 (4.5, 0, 15) -> advances to DEST
    out2 = mc.compute_control_step((4.5, 0.0, 15.0), (2.0, 0.0, 0.0), _clear_obs())
    assert "WP_1" in mc.reached_monitoring_ids
    assert out2.active_waypoint_id == "DEST"
    assert not out2.mission_completed

    # Within tolerance of DEST (9.5, 0, 15) -> completes mission and commands hover
    out3 = mc.compute_control_step((9.5, 0.0, 15.0), (1.0, 0.0, 0.0), _clear_obs())
    assert out3.mission_completed is True
    assert np.allclose(out3.final_action_xyz, (0.0, 0.0, 0.0))


def _is_airsim_server_listening(host: str = "127.0.0.1", port: int = 41451) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


@pytest.mark.skipif(
    not _is_airsim_server_listening(),
    reason="Optional AirSim integration test skipped: AirSim RPC server is not running on 127.0.0.1:41451.",
)
def test_optional_live_airsim_connection():
    client = AirSimUAVClient()
    client.connect()
    state = client.get_kinematic_state()
    assert isinstance(state.north, float)
    client.land_and_release()
