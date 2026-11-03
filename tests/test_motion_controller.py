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


def test_baseline_full_route_completion_kinematic(tmp_path):
    """Verify that the BASELINE kinematic mission completes all 6 monitoring waypoints and reaches the destination."""
    from backend.global_planner.config import PlannerConfig
    from backend.global_planner.planner_service import GlobalPlannerService
    from backend.intelligent_control.mission_runner import MissionRunner
    from backend.intelligent_control.route_loader import load_global_route

    p_cfg = PlannerConfig.from_json_file("configs/default_environment.json")
    p_cfg.export_plots = False
    service = GlobalPlannerService(p_cfg)
    env = service.generate_environment(p_cfg.environment)
    planned = service.plan_route(env, p_cfg)
    ctrl_route_path = tmp_path / "controller_route.json"
    service.export_controller_route(planned, ctrl_route_path, environment=env)

    route = load_global_route(ctrl_route_path)
    ctrl_cfg = ControllerConfig()
    safety_cfg = SafetyConfig()
    runner = MissionRunner(ctrl_cfg, safety_cfg, td3_agent=None)

    res = runner.run_mission(
        route=route,
        nav_mode="BASELINE",
        execution_backend="kinematic",
        include_dynamic_obstacles=False,
        seed=42,
        process_noise_std_mps=0.0,
    )
    assert res.success is True
    assert res.termination_reason == "SUCCESS_COMPLETED"
    assert res.reached_final_destination is True
    assert res.monitoring_waypoints_reached == 6
    assert res.monitoring_waypoints_total == 6
    assert res.monitoring_coverage_ratio == 1.0
    assert res.collision_count == 0
    assert res.final_distance_to_destination_m <= ctrl_cfg.control.destination_tolerance_m
    assert res.visited_monitoring_waypoints == [w.waypoint_id for w in route.monitoring_waypoints]


def test_timeout_handling_when_step_budget_too_small():
    """Verify that MissionRunner reports MAX_STEPS_TIMEOUT and success=False if step limit is exhausted."""
    from backend.intelligent_control.mission_runner import MissionRunner
    from backend.intelligent_control.route_loader import load_global_route

    route = load_global_route("configs/sample_global_route.json")
    ctrl_cfg = ControllerConfig()
    ctrl_cfg.control.max_mission_steps = 10
    safety_cfg = SafetyConfig()
    runner = MissionRunner(ctrl_cfg, safety_cfg, td3_agent=None)

    res = runner.run_mission(
        route=route,
        nav_mode="BASELINE",
        execution_backend="kinematic",
        include_dynamic_obstacles=False,
        seed=42,
    )
    assert res.success is False
    assert res.termination_reason == "MAX_STEPS_TIMEOUT"
    assert res.reached_final_destination is False


def test_airsim_cleanup_called_on_exception(monkeypatch):
    """Verify that _run_airsim_mission always calls land_and_release() in its finally block even on exception."""
    from backend.intelligent_control.mission_runner import MissionRunner
    from backend.intelligent_control.route_loader import load_global_route

    cleanup_called = {"count": 0}

    class DummyFailedAirSimClient:
        def __init__(self, config=None):
            self.config = config

        def connect(self):
            pass

        def reset_vehicle(self):
            pass

        def enable_api_control(self):
            pass

        def arm_and_takeoff(self, altitude_m=None):
            raise RuntimeError("Simulated mid-takeoff RPC error")

        def land_and_release(self):
            cleanup_called["count"] += 1

    monkeypatch.setattr("backend.intelligent_control.mission_runner.AirSimUAVClient", DummyFailedAirSimClient)

    route = load_global_route("configs/sample_global_route.json")
    ctrl_cfg = ControllerConfig()
    safety_cfg = SafetyConfig()
    runner = MissionRunner(ctrl_cfg, safety_cfg, td3_agent=None)

    with pytest.raises(RuntimeError, match="Simulated mid-takeoff RPC error"):
        runner.run_mission(
            route=route,
            nav_mode="BASELINE",
            execution_backend="airsim",
            include_dynamic_obstacles=False,
        )
    assert cleanup_called["count"] == 1
