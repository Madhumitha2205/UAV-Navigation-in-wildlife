"""Mission Runner for Local UAV Navigation (AirSim and Dry-Run Kinematic Execution).

Responsibilities:
- Loads and validates the Global Route JSON.
- Initializes either:
  (1) A live AirSim connection (`execution_backend="airsim"`), or
  (2) A simulation-free kinematic dry-run/evaluation backend (`execution_backend="kinematic"`).
- Executes the mission through ordered waypoints using `MotionController`.
- Enforces explicit success criteria (waypoint coverage, final destination tolerance,
  collision-free status, and time/step limits).
- Ensures safe hover, landing, and API control release in `finally` cleanup blocks.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from backend.intelligent_control.airsim_client import AirSimUAVClient
from backend.intelligent_control.airsim_sensors import AirSimSensorReader, ObstacleObservation
from backend.intelligent_control.config import ControllerConfig, SafetyConfig
from backend.intelligent_control.coordinate_transform import CoordinateTransformer
from backend.intelligent_control.curriculum import CurriculumManager
from backend.intelligent_control.motion_controller import MotionController
from backend.intelligent_control.rl_environment import DynamicObstacle
from backend.intelligent_control.route_loader import GlobalRoute, load_global_route
from backend.intelligent_control.td3_agent import TD3Agent

logger = logging.getLogger(__name__)


@dataclass
class MissionResult:
    """Structured mission result with explicit success criteria and recorded metrics."""
    mission_id: str
    nav_mode: str
    execution_backend: str  # 'airsim' or 'kinematic_dry_run'
    success: bool
    termination_reason: str
    reached_final_destination: bool
    monitoring_waypoints_reached: int
    monitoring_waypoints_total: int
    monitoring_coverage_ratio: float
    visited_monitoring_waypoints: List[str]
    final_position_xyz: Tuple[float, float, float]
    final_distance_to_destination_m: float
    collision_count: int
    has_collided: bool
    min_obstacle_distance_m: float
    total_travelled_distance_m: float
    planned_route_length_m: float
    steps_executed: int
    planning_time_sec: float
    execution_time_sec: float
    simulated_flight_duration_sec: float
    fuzzy_intervention_count: int
    fuzzy_intervention_rate: float
    control_smoothness_rms_jerk_mps2: float
    estimated_energy_proxy_joules: float
    energy_proxy_model_note: str = (
        "Estimated kinematic control-effort proxy (NOT physical battery measurement): "
        "integral of (P_hover + k_v * ||v||^2 + k_a * ||dv/dt||^2) dt"
    )
    trajectory_xyz: List[Tuple[float, float, float]] = field(default_factory=list)
    intervention_logs: List[Dict[str, Any]] = field(default_factory=list)

    def to_summary_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("trajectory_xyz", None)
        d.pop("intervention_logs", None)
        return d


class MissionRunner:
    """Executes a global route using the TD3 + Fuzzy Safety motion controller."""

    def __init__(
        self,
        controller_config: ControllerConfig,
        safety_config: SafetyConfig,
        td3_agent: Optional[TD3Agent] = None,
    ) -> None:
        self.cfg = controller_config
        self.safety_cfg = safety_config
        self.td3_agent = td3_agent
        self.transformer = CoordinateTransformer(controller_config.coordinate_mapping)
        self.sensor_reader = AirSimSensorReader(controller_config.airsim, max_lidar_range_m=50.0)

    def run_mission(
        self,
        route: GlobalRoute | str | Path,
        nav_mode: str = "TD3_WITH_FUZZY_SAFETY",
        execution_backend: str = "kinematic",
        include_dynamic_obstacles: bool = True,
        seed: int = 42,
        process_noise_std_mps: float = 0.08,
    ) -> MissionResult:
        """Run a full mission in either 'kinematic' (dry-run/local eval) or 'airsim' mode."""
        if isinstance(route, (str, Path)):
            global_route = load_global_route(route)
        else:
            global_route = route

        if execution_backend not in ("kinematic", "airsim"):
            raise ValueError("execution_backend must be 'kinematic' or 'airsim'.")

        use_safety = nav_mode == "TD3_WITH_FUZZY_SAFETY"
        controller = MotionController(
            controller_config=self.cfg,
            safety_config=self.safety_cfg,
            route_points=global_route.intermediate_path_points,
            td3_agent=self.td3_agent,
            nav_mode=nav_mode,
            use_safety_layer=use_safety,
        )

        obstacles = CurriculumManager.build_evaluation_route_obstacles(
            global_route.static_obstacles,
            include_dynamic=include_dynamic_obstacles,
        )

        if execution_backend == "airsim":
            return self._run_airsim_mission(global_route, controller, obstacles, nav_mode)
        return self._run_kinematic_mission(
            global_route=global_route,
            controller=controller,
            obstacles=obstacles,
            nav_mode=nav_mode,
            seed=seed,
            process_noise_std_mps=process_noise_std_mps,
        )

    def _run_kinematic_mission(
        self,
        global_route: GlobalRoute,
        controller: MotionController,
        obstacles: List[DynamicObstacle],
        nav_mode: str,
        seed: int = 42,
        process_noise_std_mps: float = 0.08,
    ) -> MissionResult:
        """Execute mission using the lightweight 3D kinematic model (no Unreal Engine required)."""
        t0_wall = time.perf_counter()
        rng = np.random.default_rng(seed)

        dt = 1.0 / max(self.cfg.control.control_frequency_hz, 1.0)
        max_steps = int(self.cfg.control.max_mission_steps)
        limits = self.cfg.vehicle_limits

        uav_pos = np.array(
            [
                global_route.start_position.x,
                global_route.start_position.y,
                global_route.start_position.z,
            ],
            dtype=np.float64,
        )
        uav_vel = np.zeros(3, dtype=np.float64)
        for obs in obstacles:
            obs.reset()

        trajectory: List[Tuple[float, float, float]] = [(float(uav_pos[0]), float(uav_pos[1]), float(uav_pos[2]))]
        velocities: List[np.ndarray] = []
        travelled_dist = 0.0
        min_obs_dist = 50.0
        collision_count = 0
        was_in_collision = False
        elapsed_sim_sec = 0.0
        termination_reason = "MAX_STEPS_TIMEOUT"
        reached_dest = False

        for step in range(1, max_steps + 1):
            spheres = [
                (float(o.center_xyz[0]), float(o.center_xyz[1]), float(o.center_xyz[2]), float(o.radius))
                for o in obstacles
            ]
            obs_vels = [
                (
                    float(o.current_velocity[0]),
                    float(o.current_velocity[1]),
                    float(o.current_velocity[2]),
                )
                for o in obstacles
            ]
            obs_reading = self.sensor_reader.compute_observation_from_spheres(
                uav_pos_xyz=uav_pos,
                uav_vel_xyz=uav_vel,
                obstacles_xyz_r=spheres,
                obstacle_vels_xyz=obs_vels,
                uav_radius_m=self.safety_cfg.collision_radius_m * 0.5,
                sensor_mode="KINEMATIC_SCENARIO_SENSOR",
            )

            if math.isfinite(obs_reading.closest_distance_m):
                min_obs_dist = min(min_obs_dist, float(obs_reading.closest_distance_m))

            if obs_reading.has_collided and not was_in_collision:
                collision_count += 1
                was_in_collision = True
            elif not obs_reading.has_collided:
                was_in_collision = False

            ctrl_out = controller.compute_control_step(uav_pos, uav_vel, obs_reading)
            for mon_id in ctrl_out.newly_reached_monitoring_ids:
                logger.info(
                    "[Kinematic][Step %d] Reached monitoring waypoint '%s' (%d/%d) at pos=(%.2f, %.2f, %.2f) m",
                    step,
                    mon_id,
                    len(controller.reached_monitoring_ids),
                    len(global_route.monitoring_waypoints),
                    uav_pos[0],
                    uav_pos[1],
                    uav_pos[2],
                )
            if step == 1 or step % 50 == 0 or ctrl_out.mission_completed:
                logger.info(
                    "[Kinematic][Step %d] pos=(%.2f, %.2f, %.2f) target_idx=%d/%d (%s) dist=%.2fm mon=%d/%d",
                    step,
                    uav_pos[0],
                    uav_pos[1],
                    uav_pos[2],
                    ctrl_out.active_waypoint_index,
                    len(controller.route_points) - 1,
                    ctrl_out.active_waypoint_id or "path",
                    ctrl_out.distance_to_target_m,
                    len(controller.reached_monitoring_ids),
                    len(global_route.monitoring_waypoints),
                )
            if ctrl_out.mission_completed:
                reached_dest = True
                termination_reason = (
                    "SUCCESS_COMPLETED" if collision_count == 0 else "COMPLETED_WITH_COLLISIONS"
                )
                break

            cmd_vel = np.asarray(ctrl_out.final_action_xyz, dtype=np.float64)
            if process_noise_std_mps > 0.0:
                disturbance = rng.normal(0.0, process_noise_std_mps, size=3)
                disturbance[2] *= 0.3
            else:
                disturbance = np.zeros(3, dtype=np.float64)

            max_dv = limits.max_acceleration_mps2 * dt
            dv = np.clip((cmd_vel + disturbance) - uav_vel, -max_dv, max_dv)
            next_vel = np.clip(uav_vel + dv, -controller.max_vel, controller.max_vel)
            next_pos = uav_pos + 0.5 * (uav_vel + next_vel) * dt

            step_dist = float(np.linalg.norm(next_pos - uav_pos))
            travelled_dist += step_dist
            uav_pos = next_pos
            uav_vel = next_vel
            elapsed_sim_sec += dt

            trajectory.append((float(uav_pos[0]), float(uav_pos[1]), float(uav_pos[2])))
            velocities.append(uav_vel.copy())

            for obs in obstacles:
                obs.step(dt, elapsed_sim_sec)

            if elapsed_sim_sec >= self.cfg.control.max_mission_time_sec:
                termination_reason = "MAX_TIME_EXCEEDED"
                break

        exec_wall_sec = time.perf_counter() - t0_wall
        return self._compile_mission_result(
            global_route=global_route,
            controller=controller,
            nav_mode=nav_mode,
            execution_backend="kinematic_dry_run",
            reached_dest=reached_dest,
            collision_count=collision_count,
            min_obs_dist=min_obs_dist,
            travelled_dist=travelled_dist,
            steps_executed=controller.step_index,
            exec_wall_sec=exec_wall_sec,
            sim_duration_sec=elapsed_sim_sec,
            termination_reason=termination_reason,
            trajectory=trajectory,
            velocities=velocities,
            dt=dt,
        )

    def _run_airsim_mission(
        self,
        global_route: GlobalRoute,
        controller: MotionController,
        obstacles: List[DynamicObstacle],
        nav_mode: str,
    ) -> MissionResult:
        """Execute mission against a live connected AirSim multirotor simulation."""
        t0_wall = time.perf_counter()
        client = AirSimUAVClient(self.cfg.airsim)
        dt = float(self.cfg.control.command_duration_sec)
        max_steps = int(self.cfg.control.max_mission_steps)

        trajectory: List[Tuple[float, float, float]] = []
        velocities: List[np.ndarray] = []
        travelled_dist = 0.0
        min_obs_dist = 50.0
        collision_count = 0
        was_in_collision = False
        elapsed_sim_sec = 0.0
        reached_dest = False
        termination_reason = "INTERRUPTED"

        try:
            client.connect()
            client.reset_vehicle()
            client.enable_api_control()

            # Compute exact route start position in AirSim NED frame before takeoff
            start_n, start_e, start_d = self.transformer.planner_to_airsim_pos(
                (
                    global_route.start_position.x,
                    global_route.start_position.y,
                    global_route.start_position.z,
                )
            )
            client.arm_and_takeoff(altitude_m=abs(start_d))

            kin0 = client.get_kinematic_state()
            dist_to_start_ned = math.hypot(kin0.north - start_n, kin0.east - start_e)
            if dist_to_start_ned > 0.5 or abs(kin0.down - start_d) > 0.5:
                logger.info(
                    "Moving UAV from spawn NED=(%.2f, %.2f, %.2f) to route start NED=(%.2f, %.2f, %.2f) [Planner=(%.1f, %.1f, %.1f)]",
                    kin0.north,
                    kin0.east,
                    kin0.down,
                    start_n,
                    start_e,
                    start_d,
                    global_route.start_position.x,
                    global_route.start_position.y,
                    global_route.start_position.z,
                )
                client.move_to_position_ned(
                    north=start_n,
                    east=start_e,
                    down=start_d,
                    velocity=min(4.0, self.cfg.vehicle_limits.max_velocity_xy_mps),
                    timeout_sec=max(20.0, self.cfg.airsim.timeout_sec * 2.0),
                )

            kin = client.get_kinematic_state()
            prev_pos = np.asarray(
                self.transformer.airsim_to_planner_pos((kin.north, kin.east, kin.down)),
                dtype=np.float64,
            )
            trajectory.append((float(prev_pos[0]), float(prev_pos[1]), float(prev_pos[2])))

            for step in range(1, max_steps + 1):
                kin = client.get_kinematic_state()
                uav_pos = np.asarray(
                    self.transformer.airsim_to_planner_pos((kin.north, kin.east, kin.down)),
                    dtype=np.float64,
                )
                uav_vel = np.asarray(
                    self.transformer.airsim_to_planner_vel((kin.vn, kin.ve, kin.vd)),
                    dtype=np.float64,
                )
                if not np.all(np.isfinite(uav_pos)) or not np.all(np.isfinite(uav_vel)):
                    termination_reason = "INVALID_STATE_ABORT"
                    logger.error("[AirSim][Step %d] Non-finite UAV state detected; aborting safely.", step)
                    client.hover_and_stop()
                    break

                travelled_dist += float(np.linalg.norm(uav_pos - prev_pos))
                prev_pos = uav_pos.copy()
                trajectory.append((float(uav_pos[0]), float(uav_pos[1]), float(uav_pos[2])))
                velocities.append(uav_vel.copy())

                sim_collided, col_obj = self.sensor_reader.read_collision_info(client)
                # Ignore initial ground contact tag ('Ground') if UAV is airborne well above ground
                if sim_collided and "ground" in col_obj.lower() and uav_pos[2] > 2.0:
                    sim_collided = False
                    col_obj = ""

                spheres = [
                    (float(o.center_xyz[0]), float(o.center_xyz[1]), float(o.center_xyz[2]), float(o.radius))
                    for o in obstacles
                ]
                obs_vels = [
                    (
                        float(o.current_velocity[0]),
                        float(o.current_velocity[1]),
                        float(o.current_velocity[2]),
                    )
                    for o in obstacles
                ]
                sphere_obs = self.sensor_reader.compute_observation_from_spheres(
                    uav_pos_xyz=uav_pos,
                    uav_vel_xyz=uav_vel,
                    obstacles_xyz_r=spheres,
                    obstacle_vels_xyz=obs_vels,
                    sensor_mode="GEOMETRIC_SCENARIO_FALLBACK",
                )

                lidar_pts_ned = self.sensor_reader.read_lidar_points_ned(client)
                if lidar_pts_ned is not None:
                    if len(lidar_pts_ned) > 0:
                        rel_pts_xyz = np.array(
                            [self.transformer.airsim_to_planner_vel(pt) for pt in lidar_pts_ned],
                            dtype=np.float64,
                        )
                    else:
                        rel_pts_xyz = np.empty((0, 3), dtype=np.float64)
                    lidar_obs = self.sensor_reader.compute_observation_from_points(
                        relative_points_xyz=rel_pts_xyz,
                        uav_vel_xyz=uav_vel,
                        has_collided=sim_collided,
                        sensor_mode="LIDAR",
                    )
                    if sphere_obs.closest_distance_m < lidar_obs.closest_distance_m:
                        obs_reading = sphere_obs
                        obs_reading.sensor_mode = "LIDAR+SCENARIO"
                    else:
                        obs_reading = lidar_obs
                    if sim_collided or sphere_obs.has_collided:
                        obs_reading.has_collided = True
                        obs_reading.collided_object_name = col_obj or sphere_obs.collided_object_name
                else:
                    obs_reading = sphere_obs
                    if sim_collided:
                        obs_reading.has_collided = True
                        obs_reading.collided_object_name = col_obj

                if math.isfinite(obs_reading.closest_distance_m):
                    min_obs_dist = min(min_obs_dist, float(obs_reading.closest_distance_m))

                if obs_reading.has_collided and not was_in_collision:
                    collision_count += 1
                    was_in_collision = True
                    termination_reason = f"COLLISION_ABORT ({obs_reading.collided_object_name or 'obstacle'})"
                    logger.error(
                        "[AirSim][Step %d] Collision detected with '%s' at pos=(%.2f, %.2f, %.2f); stopping safely.",
                        step,
                        obs_reading.collided_object_name or "obstacle",
                        uav_pos[0],
                        uav_pos[1],
                        uav_pos[2],
                    )
                    client.hover_and_stop()
                    break
                elif not obs_reading.has_collided:
                    was_in_collision = False

                ctrl_out = controller.compute_control_step(uav_pos, uav_vel, obs_reading)
                for mon_id in ctrl_out.newly_reached_monitoring_ids:
                    logger.info(
                        "[AirSim][Step %d] Reached monitoring waypoint '%s' (%d/%d) at planner=(%.2f, %.2f, %.2f) NED=(%.2f, %.2f, %.2f)",
                        step,
                        mon_id,
                        len(controller.reached_monitoring_ids),
                        len(global_route.monitoring_waypoints),
                        uav_pos[0],
                        uav_pos[1],
                        uav_pos[2],
                        kin.north,
                        kin.east,
                        kin.down,
                    )
                if step == 1 or step % 20 == 0 or ctrl_out.mission_completed:
                    logger.info(
                        "[AirSim][Step %d] planner=(%.2f, %.2f, %.2f) NED=(%.2f, %.2f, %.2f) target_idx=%d/%d (%s) dist=%.2fm mon=%d/%d",
                        step,
                        uav_pos[0],
                        uav_pos[1],
                        uav_pos[2],
                        kin.north,
                        kin.east,
                        kin.down,
                        ctrl_out.active_waypoint_index,
                        len(controller.route_points) - 1,
                        ctrl_out.active_waypoint_id or "path",
                        ctrl_out.distance_to_target_m,
                        len(controller.reached_monitoring_ids),
                        len(global_route.monitoring_waypoints),
                    )
                if ctrl_out.mission_completed:
                    reached_dest = True
                    termination_reason = (
                        "SUCCESS_COMPLETED" if collision_count == 0 else "COMPLETED_WITH_COLLISIONS"
                    )
                    break

                vn, ve, vd = self.transformer.planner_to_airsim_vel(ctrl_out.final_action_xyz)
                client.move_by_velocity_ned(vn, ve, vd, duration_sec=dt, join=True)
                elapsed_sim_sec += dt

                for obs in obstacles:
                    obs.step(dt, elapsed_sim_sec)

                if elapsed_sim_sec >= self.cfg.control.max_mission_time_sec:
                    termination_reason = "MAX_TIME_EXCEEDED"
                    break
            else:
                termination_reason = "MAX_STEPS_TIMEOUT"
        except Exception as exc:
            termination_reason = f"AIRSIM_EXCEPTION: {exc}"
            logger.error("AirSim mission aborted due to error: %s", exc)
            raise
        finally:
            client.land_and_release()

        exec_wall_sec = time.perf_counter() - t0_wall
        return self._compile_mission_result(
            global_route=global_route,
            controller=controller,
            nav_mode=nav_mode,
            execution_backend="airsim",
            reached_dest=reached_dest,
            collision_count=collision_count,
            min_obs_dist=min_obs_dist,
            travelled_dist=travelled_dist,
            steps_executed=controller.step_index,
            exec_wall_sec=exec_wall_sec,
            sim_duration_sec=elapsed_sim_sec,
            termination_reason=termination_reason,
            trajectory=trajectory,
            velocities=velocities,
            dt=dt,
        )

    def _compile_mission_result(
        self,
        global_route: GlobalRoute,
        controller: MotionController,
        nav_mode: str,
        execution_backend: str,
        reached_dest: bool,
        collision_count: int,
        min_obs_dist: float,
        travelled_dist: float,
        steps_executed: int,
        exec_wall_sec: float,
        sim_duration_sec: float,
        termination_reason: str,
        trajectory: List[Tuple[float, float, float]],
        velocities: List[np.ndarray],
        dt: float,
    ) -> MissionResult:
        total_mon = len(global_route.monitoring_waypoints)
        reached_mon = len(controller.reached_monitoring_ids)
        coverage = float(reached_mon) / max(1, total_mon)

        # Explicit strict success criteria:
        # 1. All monitoring waypoints reached
        # 2. Final destination reached within tolerance
        # 3. Zero collisions
        # 4. Completed within step/time limits
        strict_success = bool(
            reached_dest
            and (reached_mon == total_mon)
            and (collision_count == 0)
        )

        # Control smoothness measure: Root-Mean-Square (RMS) acceleration / velocity change rate (m/s^2)
        if len(velocities) >= 2:
            vel_arr = np.asarray(velocities, dtype=np.float64)
            accels = np.diff(vel_arr, axis=0) / max(dt, 1e-4)
            accel_norms_sq = np.sum(accels ** 2, axis=1)
            rms_smoothness = float(np.sqrt(np.mean(accel_norms_sq)))
        else:
            vel_arr = np.zeros((1, 3), dtype=np.float64)
            accels = np.zeros((1, 3), dtype=np.float64)
            rms_smoothness = 0.0

        # Documented Estimated Control-Effort / Energy Proxy (Joules-equivalent proxy):
        # E_proxy = sum_t (P_hover_base + k_v * ||v_t||^2 + k_a * ||a_t||^2) * dt
        # where P_hover_base = 120.0 W, k_v = 4.5 W/(m/s)^2, k_a = 6.0 W/(m/s^2)^2
        p_hover = 120.0
        k_v = 4.5
        k_a = 6.0
        if len(velocities) > 0:
            v_sq = np.sum(np.asarray(velocities, dtype=np.float64) ** 2, axis=1)
            a_sq = (
                np.sum(accels ** 2, axis=1)
                if len(velocities) >= 2
                else np.zeros(len(velocities), dtype=np.float64)
            )
            if len(a_sq) < len(v_sq):
                a_sq = np.pad(a_sq, (0, len(v_sq) - len(a_sq)), mode="edge")
            inst_power = p_hover + k_v * v_sq + k_a * a_sq
            energy_proxy = float(np.sum(inst_power) * dt)
        else:
            energy_proxy = 0.0

        num_interventions = len(controller.intervention_logs)
        intervention_rate = float(num_interventions) / max(1, steps_executed)

        planning_time = float(global_route.validation.get("planning_time_sec", 0.0))
        planned_length = float(global_route.path_metrics.get("planned_path_length_m", 0.0))

        if trajectory:
            final_pos = (
                round(float(trajectory[-1][0]), 4),
                round(float(trajectory[-1][1]), 4),
                round(float(trajectory[-1][2]), 4),
            )
        else:
            final_pos = (
                round(float(global_route.start_position.x), 4),
                round(float(global_route.start_position.y), 4),
                round(float(global_route.start_position.z), 4),
            )

        dest_vec = np.array(
            [
                global_route.destination.x,
                global_route.destination.y,
                global_route.destination.z,
            ],
            dtype=np.float64,
        )
        final_dist_to_dest = float(np.linalg.norm(dest_vec - np.asarray(final_pos, dtype=np.float64)))

        return MissionResult(
            mission_id=global_route.mission_id,
            nav_mode=nav_mode,
            execution_backend=execution_backend,
            success=strict_success,
            termination_reason=termination_reason,
            reached_final_destination=reached_dest,
            monitoring_waypoints_reached=reached_mon,
            monitoring_waypoints_total=total_mon,
            monitoring_coverage_ratio=round(coverage, 4),
            visited_monitoring_waypoints=list(controller.reached_monitoring_ids),
            final_position_xyz=final_pos,
            final_distance_to_destination_m=round(final_dist_to_dest, 4),
            collision_count=collision_count,
            has_collided=bool(collision_count > 0),
            min_obstacle_distance_m=round(float(min_obs_dist), 4),
            total_travelled_distance_m=round(float(travelled_dist), 4),
            planned_route_length_m=round(planned_length, 4),
            steps_executed=steps_executed,
            planning_time_sec=round(planning_time, 4),
            execution_time_sec=round(exec_wall_sec, 4),
            simulated_flight_duration_sec=round(sim_duration_sec, 4),
            fuzzy_intervention_count=num_interventions,
            fuzzy_intervention_rate=round(intervention_rate, 4),
            control_smoothness_rms_jerk_mps2=round(rms_smoothness, 4),
            estimated_energy_proxy_joules=round(energy_proxy, 2),
            trajectory_xyz=trajectory,
            intervention_logs=list(controller.intervention_logs),
        )
