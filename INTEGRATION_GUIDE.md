# Global Planner (Part 1) ↔ Local Controller (Part 2) Integration Specification

## 1. Overview
This document specifies the formal interface between:
- **Part 1 (Global Planner)**: Genetic Algorithm (GA) + 2-Opt + A* global route optimization.
- **Part 2 (Local Controller & Safety)**: Twin Delayed Deep Deterministic Policy Gradient (TD3) + Adaptive Fuzzy Logic (AFL) safety layer + AirSim multirotor execution.

Coordinate with the Part 1 developer before changing any field names or units. `backend/intelligent_control/route_loader.py` strictly validates this schema and rejects malformed or unsuccessful planning outputs.

---

## 2. Input Contract: Global Route JSON Schema
Part 1 exports a JSON file (default path: `configs/sample_global_route.json` or passed via `--route <path>`).

### Required Top-Level Fields
| Field | Type | Description |
|---|---|---|
| `mission_id` | `string` | Unique identifier for the wildlife monitoring mission. |
| `planner_algorithm` | `string` | Algorithm identifier (e.g., `"GA_2Opt_AStar"`). |
| `coordinate_convention` | `object` | Must contain `"frame"` (e.g., `"ENU_ALT_UP"`), `"units": "metres"`, and axis descriptions (`x`: East, `y`: North, `z`: Altitude positive up). |
| `validation` | `object` | Must contain `"is_valid": true`, `"status": "SUCCESS"`, `"collision_free": true`, and `"planning_time_sec"` (float). Routes with `is_valid: false` or `collision_free: false` are rejected. |
| `start_position` | `object` | `{"x": float, "y": float, "z": float}` in metres. |
| `destination` | `object` | `{"x": float, "y": float, "z": float}` in metres. |
| `monitoring_waypoints` | `array` | Non-empty ordered list of wildlife monitoring waypoints: `[{"id": "WP_1", "x": float, "y": float, "z": float, "zone_name": string, "priority": int}, ...]`. |
| `intermediate_path_points` | `array` | Ordered list (length ≥ 2) of 3D path points connecting `start_position` through `monitoring_waypoints` to `destination`: `[{"x": float, "y": float, "z": float, "is_monitoring": bool, "waypoint_id": string|null}, ...]`. |
| `path_metrics` | `object` | Must include `"planned_path_length_m"` (> 0), `"num_monitoring_waypoints"`, and `"num_total_points"`. |
| `static_obstacles` | `array` (optional) | Known static obstacles: `[{"id": string, "x": float, "y": float, "z": float, "radius": float}, ...]`. |

---

## 3. Coordinate Transformation (Planner ↔ AirSim NED)
Implemented in `backend/intelligent_control/coordinate_transform.py` and configured in `configs/controller_config.json` under `"coordinate_mapping"`:
- **Global Planner Frame (`ENU_ALT_UP`)**:
  - $X$: East (metres)
  - $Y$: North (metres)
  - $Z$: Altitude, positive **UP** (metres)
- **AirSim Multirotor Frame (`NED`)**:
  - $\text{North} = +Y_{\text{planner}}$ (`x_to_north = 0.0`, `y_to_north = 1.0`)
  - $\text{East} = +X_{\text{planner}}$ (`x_to_east = 1.0`, `y_to_east = 0.0`)
  - $\text{Down} = -Z_{\text{planner}}$ (`z_sign = -1.0`)

The same bi-directional transformation is applied consistently to:
1. Planned waypoints and intermediate path points (`planner_to_airsim_pos`)
2. AirSim UAV position and velocity (`airsim_to_planner_pos`, `airsim_to_planner_vel`)
3. Local controller velocity commands (`planner_to_airsim_vel`)
4. Obstacle coordinates (`convert_obstacles_to_airsim`)

---

## 4. Output Contract from Part 2 (Local Controller)
After executing a mission or comparative evaluation, Part 2 produces:
1. **`logs/dry_run_result.json` or `logs/airsim_mission_result.json`**:
   - `mission_id`, `nav_mode`, `execution_backend`, `success` (strict boolean), `termination_reason`
   - `monitoring_waypoints_reached`, `monitoring_waypoints_total`, `monitoring_coverage_ratio`
   - `collision_count`, `min_obstacle_distance_m`
   - `planned_route_length_m` vs. `total_travelled_distance_m`
   - `planning_time_sec` (from Part 1) and `execution_time_sec` (from Part 2)
   - `fuzzy_intervention_count`, `fuzzy_intervention_rate`
   - `control_smoothness_rms_jerk_mps2`
   - `estimated_energy_proxy_joules` (explicitly labeled as a kinematic control-effort proxy)
2. **`logs/evaluation_summary.csv` & `logs/evaluation_trials.csv`**:
   - Multi-seed comparative metrics across Configurations A (Baseline), B (TD3 without Fuzzy Safety), and C (TD3 with Fuzzy Safety).
3. **`outputs/trajectory_comparison.png` & `outputs/metrics_comparison.png`**:
   - Visual comparison of the Part 1 planned route against the actual flown trajectories.
