# An Intelligent Hierarchical UAV Navigation Framework for Safe and Energy-Efficient Wildlife Monitoring in Dynamic Environments

This repository contains an integrated UAV navigation framework consisting of two complementary modules:

- **Part 1 – Global Route Planning:** Obstacle-aware surveillance route generation using a hybrid Genetic Algorithm (GA), 2-Opt local search, and A* pathfinding.
- **Part 2 – Local Navigation and Safety:** Baseline waypoint tracking, TD3-based local movement control, Adaptive Fuzzy Logic (AFL) safety override, and 3D AirSim Blocks integration.

The framework generates validated global monitoring routes, converts them automatically into the controller schema, verifies them in a lightweight 3D kinematic simulator, and executes them visibly on a virtual `SimpleFlight` multirotor in the 3D AirSim Blocks environment.

---

## 1. Quick Start (Beginner-Friendly End-to-End Workflow)

Run all commands from **PowerShell** in the project root (`C:\Users\madhu\OneDrive\Desktop\UAV-Navigation-in-wildlife`).

### Step 1: Generate, Validate, and Verify the Global Route in Kinematic Simulation

```powershell
.\.venv\Scripts\python.exe run_pipeline.py
```

Or run the individual stages directly:

```powershell
# 1a. Generate and validate global route (exports outputs/planned_route.json and outputs/controller_route.json)
.\.venv\Scripts\python.exe main.py --config configs/default_environment.json --output-dir outputs

# 1b. Run kinematic baseline controller on the validated route (no TD3 checkpoint or AirSim required)
.\.venv\Scripts\python.exe td3_main.py --mode baseline
```

### Step 2: Start the 3D AirSim Blocks Simulator

Open the AirSim Blocks 3D window before running any AirSim flight command:

```powershell
Start-Process "D:\AirSimEnvironments\Blocks\Blocks\WindowsNoEditor\Blocks\Binaries\Win64\Blocks.exe" -ArgumentList "-ResX=1280","-ResY=720","-windowed"
```

Verify that AirSim is listening on `127.0.0.1:41451` and that `SimpleFlight` and `LidarSensor1` are ready:

```powershell
.\.venv\Scripts\python.exe scripts/verify_airsim_connection.py
```

### Step 3: Spawn 3D Wildlife Obstacles & Fly the Virtual UAV in AirSim 3D Blocks

You can optionally spawn visible 3D scene representations of the global planner's obstacle regions (`dense_canopy_01`, `mountain_ridge_01`, `elephant_herd_snapshot`) inside AirSim Blocks before flying:

```powershell
# 3a. Spawn the complete 24-actor 3D obstacle layout in AirSim Blocks
.\.venv\Scripts\python.exe scripts/manage_airsim_obstacles.py --action spawn

# 3b. Run the AirSim 3D baseline route-following flight (with --spawn-obstacles to ensure layout is active)
.\.venv\Scripts\python.exe td3_main.py --mode airsim-baseline --spawn-obstacles

# 3c. Or run the full end-to-end pipeline with 3D obstacle spawning enabled
.\.venv\Scripts\python.exe run_pipeline.py --airsim --spawn-obstacles

# 3d. Clean up ONLY project-created (wl_obs_*) 3D obstacles while preserving all pre-existing Blocks actors
.\.venv\Scripts\python.exe scripts/manage_airsim_obstacles.py --action cleanup

# 3e. Run full 4-phase obstacle verification (single-obstacle test, RGB camera + LiDAR distance check, controlled collision check, and full layout spawn)
.\.venv\Scripts\python.exe scripts/manage_airsim_obstacles.py --action verify-all
```

### Optional: Fly a planned route from the web dashboard

The dashboard's live mode sends planner and flight-control requests to the unified backend on port `8001`. Start AirSim Blocks first and merge `configs/airsim_settings.json` into AirSim's user settings file if the `SimpleFlight` vehicle or LiDAR sensor is not configured.

```powershell
# Terminal 1, from the project root
.\.venv\Scripts\python.exe -m backend.server

# Terminal 2, from the project root
Set-Location frontend
npm run dev
```

In the dashboard, switch to **Live Backend Connection**, open **Live Monitoring**, click **Plan Route**, then **Connect AirSim** and **Start Mission**. A live mission is disabled until both a route and AirSim connection are available; the multirotor flies in the AirSim Blocks window while the dashboard displays its telemetry.

### Step 4: Train and Evaluate TD3 + Adaptive Fuzzy Safety

Modes that use the TD3 neural policy (`--mode dry-run`, `--mode evaluate`, `--mode airsim`, or `run_pipeline.py --controller td3`) require a trained checkpoint at `models/td3_wildlife_uav.pt`.

```powershell
# 4a. Train the TD3 checkpoint in the 3-stage curriculum environment
.\.venv\Scripts\python.exe td3_main.py --mode train --episodes 150

# 4b. Run TD3 + Adaptive Fuzzy Safety in kinematic dry-run simulation
.\.venv\Scripts\python.exe td3_main.py --mode dry-run

# 4c. Run comparative evaluation (Config A: Baseline, Config B: TD3 only, Config C: TD3 + Fuzzy Safety)
.\.venv\Scripts\python.exe td3_main.py --mode evaluate --seeds 101 102 103

# 4d. Fly TD3 + Adaptive Fuzzy Safety in 3D AirSim Blocks (requires Blocks.exe running)
.\.venv\Scripts\python.exe td3_main.py --mode airsim
```

---

## 2. Architecture Overview

### Part 1: Global Route Planning (`backend/global_planner/`)

1. Environment and configuration loading (`configs/default_environment.json`).
2. Obstacle-aware 8-connected A* grid pathfinding (`grid_pathfinder.py`) with continuous grid-step preservation (`max_segment_length = grid_res * 1.5`).
3. Pairwise path-distance calculation and segment caching (`fitness.py`).
4. Genetic Algorithm for waypoint ordering (`genetic_algorithm.py`).
5. 2-Opt local route refinement (`two_opt.py`).
6. Independent route validation (`route_validator.py`) verifying start/destination endpoints, sequential waypoint coverage on the actual path geometry, step continuity, path length consistency, and obstacle clearance.
7. Authoritative planner output export (`outputs/planned_route.json`), automatic controller schema conversion (`outputs/controller_route.json`), and route visualization (`outputs/planned_route_map.png`).

### Part 2: Local Navigation, Safety & AirSim Integration (`backend/intelligent_control/`)

1. Validated route loading and schema verification (`route_loader.py`).
2. Bi-directional coordinate transformation (`coordinate_transform.py`) between Planner ENU/Altitude-Up and AirSim NED.
3. Proportional baseline waypoint tracker (`BASELINE`) and TD3 continuous velocity control (`TD3_NO_SAFETY`, `TD3_WITH_FUZZY_SAFETY`) in `motion_controller.py`.
4. 9-rule Mamdani Adaptive Fuzzy Logic safety layer (`fuzzy_safety.py`).
5. 3D kinematic simulation and curriculum training (`rl_environment.py`, `curriculum.py`).
6. Live AirSim multirotor flight lifecycle and LiDAR/collision telemetry (`airsim_client.py`, `airsim_sensors.py`, `mission_runner.py`).

---

## 3. Route Files and Coordinate Frames

### 3.1 Authoritative Route Files

- **`outputs/planned_route.json` (Authoritative Global Planner Output):** Exported by `GlobalPlannerService.export_route()`. Contains `schema_version`, `planner`, `status`, `start`, `destination`, `ordered_monitoring_waypoints`, continuous `path_points` (`271` points for the default wildlife reserve, max step `1.414 m`), `metrics`, and `validation`.
- **`outputs/controller_route.json` (Validated Controller Input):** Automatically generated from the validated `PlannedRoute` and active `Environment` obstacles by `GlobalPlannerService.export_controller_route()` (and `route_loader.convert_planned_route_file()`). Contains `start_position`, `destination`, `monitoring_waypoints`, `intermediate_path_points`, `static_obstacles`, `path_metrics`, `validation`, and `coordinate_convention`.

### 3.2 Coordinate Frame Conventions

| Interface / Module | Coordinate Frame | Axes Convention |
|---|---|---|
| Global Planner (`backend/global_planner/`) | `planner_xy_altitude_up` (`ENU_ALT_UP`) | `X` = East (m), `Y` = North (m), `Z` = Altitude positive **UP** (m) |
| Controller & Plots (`backend/intelligent_control/`) | `ENU_ALT_UP` | `X` = East (m), `Y` = North (m), `Z` = Altitude positive **UP** (m) |
| AirSim Simulator (`AirSimUAVClient`) | `NED` | `North` = `+Y_planner`, `East` = `+X_planner`, `Down` = `-Z_planner + origin_ned[2]` |

- **AirSim Blocks Vertical Reference Datum (`origin_ned`):** In the Unreal `Blocks` environment (`Blocks.exe`), pre-baked static mesh block towers (`TemplateCube_Rounded_*`) in the central courtyard extend up to `z_ned = -23.98 m` (`24 m` above the courtyard floor). In `configs/controller_config.json`, `origin_ned` is set to `[0.0, 0.0, -18.0]` so the planner's `Z = 0 m` reference ground plane maps to `Down = -18.0 m` and the nominal `Z = 10.0 m` flight altitude maps to `Down = -28.0 m` (`4.02 m` clear above the tallest static block towers while remaining directly in view above the Blocks courtyard).

---

## 4. Expected Output Files

| File Path | Description |
|---|---|
| `outputs/planned_route.json` | Authoritative global planner route JSON (`271` continuous path points, `6/6` waypoints, `294.85 m`). |
| `outputs/controller_route.json` | Automatically converted controller route JSON with environment obstacles and validation status. |
| `outputs/planned_route_map.png` | 2D visualization of the planned wildlife monitoring route, waypoints, and obstacles. |
| `outputs/ga_convergence.png` | Genetic Algorithm + 2-Opt fitness convergence plot across generations. |
| `outputs/baseline_kinematic_result.json` | Mission summary JSON for the kinematic `BASELINE` run. |
| `outputs/baseline_kinematic_trajectory.csv` | Recorded step-by-step `(x, y, z)` trajectory for the kinematic `BASELINE` run. |
| `outputs/baseline_kinematic_trajectory.png` | 2D trajectory plot comparing planned route vs. flown kinematic baseline trajectory. |
| `outputs/airsim_baseline_result.json` | Mission summary JSON for the live 3D AirSim Blocks `BASELINE` flight. |
| `outputs/airsim_baseline_trajectory.csv` | Recorded step-by-step `(x, y, z)` trajectory from live 3D AirSim flight. |
| `outputs/airsim_baseline_trajectory.png` | 2D trajectory plot of the actual 3D AirSim Blocks flight path. |
| `models/td3_wildlife_uav.pt` | Trained TD3 actor/critic PyTorch checkpoint (created by `--mode train`). |
| `models/td3_wildlife_uav.meta.json` | Metadata sidecar for the trained TD3 checkpoint. |
| `outputs/td3_dry_run_result.json` | Mission summary JSON for `TD3_WITH_FUZZY_SAFETY` kinematic dry-run. |
| `outputs/td3_dry_run_trajectory.png` | Trajectory plot for `TD3_WITH_FUZZY_SAFETY` kinematic dry-run. |
| `outputs/comparative_trajectory_plot.png` | Comparative trajectory plot across Baseline, TD3-only, and TD3 + Fuzzy Safety. |
| `outputs/comparative_metrics_bar_chart.png` | Comparative metrics bar chart across evaluated configurations. |
| `logs/controller_execution.log` | Detailed timestamped mission execution log including waypoint-reached events. |

---

## 5. Running Automated Tests

Run the full unit and integration test suite using the repository's `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pytest -v -rs
```

Check package dependency health:

```powershell
.\.venv\Scripts\python.exe -m pip check
```

---

## 6. Troubleshooting

1. **AirSim Connection Refused (`127.0.0.1:41451`):**
   - Ensure `Blocks.exe` is running (`Start-Process "D:\AirSimEnvironments\Blocks\Blocks\WindowsNoEditor\Blocks\Binaries\Win64\Blocks.exe" -ArgumentList "-ResX=1280","-ResY=720","-windowed"`).
   - Run `.\.venv\Scripts\python.exe scripts/verify_airsim_connection.py` to verify RPC connectivity, `SimpleFlight` vehicle discovery, and `LidarSensor1` point cloud streaming.
2. **Missing TD3 Checkpoint (`models/td3_wildlife_uav.pt`):**
   - Modes `--mode dry-run`, `--mode evaluate`, and `--mode airsim` refuse to execute with random untrained weights.
   - Run `.\.venv\Scripts\python.exe td3_main.py --mode train --episodes 150` to train and save `models/td3_wildlife_uav.pt`, or use `--mode baseline` / `--mode airsim-baseline` for deterministic baseline waypoint tracking.
3. **Invalid or Stale Route File (`RouteValidationError`):**
   - Regenerate both `outputs/planned_route.json` and `outputs/controller_route.json` by running `.\.venv\Scripts\python.exe main.py --config configs/default_environment.json --output-dir outputs`.

---

## 7. Known Limitations

1. **Simulation Only:** This project operates strictly in virtual simulation (kinematic and AirSim 3D Blocks) and must never be connected to a physical UAV.
2. **Kinematic Training Environment:** TD3 training uses a lightweight 3D kinematic point-mass approximation with first-order velocity response rather than full aerodynamic rotor physics.
3. **Heuristic Safety Layer:** The Adaptive Fuzzy Logic (AFL) safety layer is a heuristic reactive filter and not a formal control-barrier mathematical proof.
4. **Energy Proxy:** Reported energy values (`estimated_energy_proxy_joules`) are kinematic control-effort integrals, not physical battery discharge measurements.
5. **Static Mesh Obstacles in AirSim Blocks:** The Unreal `Blocks` map has pre-baked static mesh blocks rather than dynamic 3D animal meshes; scenario obstacles are combined with live `LidarSensor1` point clouds during flight.
