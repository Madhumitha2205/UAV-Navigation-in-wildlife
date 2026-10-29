# An Intelligent Hierarchical UAV Navigation Framework for Safe and Energy-Efficient Wildlife Monitoring in Dynamic Environments

## Part 2: AirSim Integration, TD3 Local Navigation Control, and Adaptive Fuzzy Logic (AFL) Safety

This repository contains the modular implementation of **Part 2** of the hierarchical UAV wildlife monitoring navigation architecture:
- **Part 1 (Global Planner - Companion Module)**: Genetic Algorithm (GA) + 2-Opt + A* global route optimization exporting validated 3D monitoring routes.
- **Part 2 (This Implementation)**:
  - **Global Route Integration & Coordinate Transformation**: Schema validation and bi-directional mapping between the Global Planner frame (`ENU_ALT_UP`) and AirSim's `NED` frame.
  - **Twin Delayed Deep Deterministic Policy Gradient (TD3)**: Implemented directly in PyTorch (Actor, Twin Critics, Target Networks, Replay Buffer, Target Policy Smoothing, Delayed Policy Updates) for continuous 3D velocity control (`[vx, vy, vz]`).
  - **Adaptive Fuzzy Logic (AFL) Safety Layer**: Reactive 9-rule fuzzy inference layer combining obstacle distance and closing speed with geometric repulsion and lateral tangent steering.
  - **Lightweight 3D Kinematic Environment & 5-Stage Curriculum**: Simulation-free training and evaluation environment that runs independently of Unreal Engine.
  - **AirSim Multirotor Client & Sensor Wrapper**: Explicit connection lifecycle, safe takeoff/landing, LiDAR point-cloud processing, and explicit geometric fallback when LiDAR is unconfigured.

---

## 1. Project Architecture & Folder Structure

```text
.
├── backend/
│   ├── __init__.py
│   ├── init.py
│   └── intelligent_control/
│       ├── __init__.py
│       ├── init.py
│       ├── config.py                 # Dataclasses & JSON configuration loaders
│       ├── route_loader.py           # Global planner JSON schema validator & parser
│       ├── coordinate_transform.py   # Planner (X-East, Y-North, Z-Up) <-> AirSim (NED)
│       ├── airsim_client.py          # AirSim MultirotorClient lifecycle & velocity control
│       ├── airsim_sensors.py         # Simulated LiDAR, collision info & geometric fallback
│       ├── rl_environment.py         # Lightweight 3D kinematic UAV training environment
│       ├── actor_network.py          # PyTorch TD3 Actor network (12D -> 3D bounded velocity)
│       ├── critic_network.py         # PyTorch TD3 Twin Critic networks Q1(s,a), Q2(s,a)
│       ├── replay_buffer.py          # Circular experience replay buffer
│       ├── td3_agent.py              # TD3 training step, target smoothing & checkpointing
│       ├── reward_function.py        # Multi-objective navigation reward & breakdown
│       ├── curriculum.py             # 5-stage curriculum & scripted dynamic obstacles
│       ├── fuzzy_safety.py           # Adaptive Fuzzy Logic (AFL) reactive safety layer
│       ├── motion_controller.py      # Closed-loop controller joining TD3 + AFL + bounds
│       ├── mission_runner.py         # Mission execution (AirSim & kinematic dry-run)
│       ├── evaluation.py             # Multi-seed comparative evaluation & Matplotlib plots
│       └── logging_utils.py          # CSV & JSON structured logging utilities
├── configs/
│   ├── controller_config.json        # AirSim, coordinate mapping, TD3, reward & control config
│   ├── safety_config.json            # Fuzzy distance/speed thresholds & membership parameters
│   └── sample_global_route.json      # Validated global route exported from Part 1 planner
├── models/                           # Saved PyTorch TD3 checkpoints (.pt) & metadata (.meta.json)
├── logs/                             # Training logs, fuzzy intervention CSVs & dry-run JSONs
├── outputs/                          # Comparative evaluation reports & trajectory/metric plots
├── tests/                            # Pytest unit & optional AirSim integration test suite
│   ├── test_route_loader.py
│   ├── test_coordinate_transform.py
│   ├── test_replay_buffer.py
│   ├── test_td3.py
│   ├── test_fuzzy_safety.py
│   ├── test_motion_controller.py
│   └── test_evaluation.py
├── main.py                           # CLI entry point (train | dry-run | evaluate | airsim)
├── INTEGRATION_GUIDE.md              # Formal interface spec for Part 1 Global Planner integration
├── requirements.txt                  # Verified package versions
└── README.md
```

---

## 2. System Environment, AirSim Compatibility & Installation

### Inspected Host Environment
- **OS**: Windows 10/11 (`Windows-10-10.0.26200-SP0`, AMD64, 16 logical CPU cores; WSL Ubuntu access is disabled by host permissions)
- **Python**: Python `3.11.9`
- **System RAM**: `15.40 GB` total (`~3.43 GB` available free RAM during execution)
- **Disk Space**: `~23.76 GB` free

### AirSim Version & Compatibility Notes
- **Selected Python Client**: `airsim==1.8.1` (official Microsoft AirSim Python RPC client) with `msgpack-rpc-python==0.4.1`, `msgpack-python==0.5.6`, and `tornado==4.5.3`.
- **Important Build Note for Python 3.11+**: `airsim==1.8.1` imports `numpy` and `msgpackrpc` inside its `setup.py`. Under modern `pip` PEP 517 build isolation, `pip install airsim` fails unless `numpy` and `msgpack-rpc-python` are installed first and `airsim` is installed with `--no-build-isolation --no-deps`.
- **Simulator Binary Status**: Because the host machine has ~3.4 GB available RAM and ~23.7 GB free disk space, downloading/running a multi-gigabyte Unreal Engine 4.27 editor or packaged AirSim 3D environment binary simultaneously would exceed safe memory limits. Therefore:
  - The official `airsim==1.8.1` Python client is installed and verified in `.venv`.
  - All training, dry-run validation, and comparative evaluations run in the lightweight 3D kinematic environment without requiring Unreal Engine.
  - When an external or local AirSim Unreal simulator binary (v1.8.1) is started on `127.0.0.1:41451`, `--mode airsim` and the optional live AirSim pytest integration test connect to it automatically.

### Virtual Environment Setup
```powershell
# 1. Create virtual environment
python -m venv .venv --system-site-packages

# 2. Install CPU PyTorch and core dependencies
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install msgpack-rpc-python
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps airsim
```

### Verified Package Versions
- `python`: `3.11.9`
- `torch`: `2.15.0+cpu`
- `numpy`: `2.4.4`
- `matplotlib`: `3.10.9`
- `pytest`: `9.1.1`
- `airsim`: `1.8.1`
- `msgpack-rpc-python`: `0.4.1`

---

## 3. State, Action, Reward & Model Checkpoint Format

### State Vector (`state_dim = 12`)
Built identically for both the lightweight RL environment and AirSim control in `build_state_vector()` (`rl_environment.py`):
1. `state[0:3]`: Normalized relative target position $(\Delta x, \Delta y, \Delta z) / 50.0 \in [-1, 1]^3$
2. `state[3:6]`: Normalized UAV velocity $(v_x / v_{xy,\max}, v_y / v_{xy,\max}, v_z / v_{z,\max}) \in [-1, 1]^3$
3. `state[6]`: Normalized Euclidean distance to current target waypoint $\in [0, 1]$
4. `state[7:10]`: Unit repulsion direction vector $(r_x, r_y, r_z)$ pointing away from the closest detected obstacle
5. `state[10]`: Normalized closest obstacle surface distance $d_{\text{obs}} / 30.0 \in [0, 1]$
6. `state[11]`: Sensor hazard indicator $\max(0, (d_{\text{safe}} - d_{\text{obs}}) / d_{\text{safe}}) \in [0, 1]$

*Note*: This 12-element state extends traditional 9-element navigation states (`rel_pos[3]`, `vel[3]`, `obs_repulsion[3]`) with explicit normalized target distance (`state[6]`), obstacle distance (`state[10]`), and hazard indicator (`state[11]`) for consistent scaling across variable-length route legs.

### Action Vector (`action_dim = 3`)
Continuous bounded 3D velocity command in the planner frame:
- `[velocity_x, velocity_y, velocity_z]` in metres/second (`m/s`), bounded by `[-5.0, +5.0] m/s` horizontally and `[-2.0, +2.0] m/s` vertically.

### Model Checkpoint Format (`models/td3_wildlife_uav.pt`)
Saved via `TD3Agent.save_checkpoint()` alongside a human-readable `models/td3_wildlife_uav.meta.json`:
- `actor_state_dict`, `actor_target_state_dict`, `critic_state_dict`, `critic_target_state_dict`
- `actor_optimizer_state_dict`, `critic_optimizer_state_dict`
- `total_it`, `trained_episodes`, `is_trained` (boolean guard preventing untrained policies from controlling the UAV)
- `td3_config`, `limits_config`, `extra_metadata`

---

## 4. Coordinate Mapping & Global Route JSON Format

- **Global Planner Frame (`ENU_ALT_UP`)**: $X = \text{East (m)}$, $Y = \text{North (m)}$, $Z = \text{Altitude positive UP (m)}$.
- **AirSim Frame (`NED`)**: $\text{North} = +Y$, $\text{East} = +X$, $\text{Down} = -Z$.
- Configured in `configs/controller_config.json` under `"coordinate_mapping"` and tested for exact round-trip invertibility in `tests/test_coordinate_transform.py`.
- Full route JSON schema details are documented in [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md).

---

## 5. Obstacle Scenarios & Adaptive Fuzzy Logic (AFL) Safety Layer

### Creating & Resetting Obstacle Scenarios
- **Static Obstacles**: Defined in the route JSON (`static_obstacles`) with 3D center $(x, y, z)$ and `radius`.
- **Dynamic Obstacles**: Configured via `DynamicObstacle` in `curriculum.py` and `rl_environment.py` with repeatable sinusoidal oscillation (`oscillation_amplitude_xyz`, `oscillation_freq_hz`) and linear velocity (`velocity_xyz`). Calling `obs.reset()` restores exact initial coordinates for deterministic multi-seed experiments.
- **AirSim Scene Obstacles**: Default AirSim scenes do not automatically spawn wildlife models. Use scripted scene objects or the explicit `GEOMETRIC_SCENARIO_FALLBACK` mode in `airsim_sensors.py` to inject repeatable moving hazards during simulation tests.

### Fuzzy Safety Thresholds (`configs/safety_config.json`)
- `safe_distance_m`: `6.0` metres (start of `SAFE` membership shoulder).
- `critical_distance_m`: `2.5` metres (peak of `CRITICAL` membership shoulder).
- Evaluates 9 fuzzy rules over obstacle distance (`CRITICAL`, `NEAR`, `SAFE`) and closing speed (`SLOW`, `MODERATE`, `FAST`), projecting out inward velocity components and blending with a radial + lateral tangent repulsion velocity.

---

## 6. Running Each Execution Mode

### A. Run Unit Tests (No AirSim Required)
```powershell
.\.venv\Scripts\python.exe -m pytest -v -rs
```

### B. Train TD3 in the Lightweight 3D Kinematic Environment
```powershell
.\.venv\Scripts\python.exe main.py --mode train --episodes 120
```

### C. Dry-Run Route & Controller Validation (No AirSim Required)
```powershell
.\.venv\Scripts\python.exe main.py --mode dry-run --route configs/sample_global_route.json
```

### D. Run Multi-Seed Comparative Evaluation (Configs A, B, and C)
```powershell
.\.venv\Scripts\python.exe main.py --mode evaluate --seeds 101 102 103 104 105
```

### E. Execute Trained Policy in Live AirSim Simulator
1. Configure AirSim `settings.json` in `~/Documents/AirSim/settings.json` with `SimMode: "Multirotor"` and `LidarSensor1` enabled.
2. Start the AirSim Unreal environment (`127.0.0.1:41451`).
3. Run:
```powershell
.\.venv\Scripts\python.exe main.py --mode airsim --route configs/sample_global_route.json --checkpoint models/td3_wildlife_uav.pt
```

---

## 7. Research Integrity & Known Limitations
1. **No Real-World Flight Claim**: All results are obtained in software simulation.
2. **Lightweight Kinematic vs. 3D AirSim Dynamics**: Training and comparative evaluation metrics generated offline use the lightweight 3D first-order inertial kinematic environment (`rl_environment.py`), which does not model 6-DOF rotor aerodynamics or pitch/roll attitude coupling.
3. **Reactive Fuzzy Heuristic**: The Adaptive Fuzzy Logic (AFL) layer is a reactive safety heuristic and does not constitute a formal mathematical collision-avoidance proof.
4. **Energy Metric is an Estimated Proxy**: `estimated_energy_proxy_joules` is computed from a documented kinematic control-effort model ($P_{\text{hover}} + k_v \|v\|^2 + k_a \|a\|^2$) and is not a physical battery discharge measurement.
5. **Simulated Geometric Obstacles**: Dynamic obstacles represent moving hazard zones via scripted 3D geometry rather than camera-based wildlife perception.
