# An Intelligent Hierarchical UAV Navigation Framework for Safe and Energy-Efficient Wildlife Monitoring in Dynamic Environments

This repository contains an integrated UAV navigation framework consisting of two complementary modules:

- **Part 1 – Global Route Planning:** Obstacle-aware surveillance route generation using a hybrid Genetic Algorithm (GA), 2-Opt local search, and A* pathfinding.
- **Part 2 – Local Navigation and Safety:** TD3-based local movement control, Adaptive Fuzzy Logic (AFL) safety, and AirSim integration.

The framework is designed to generate global monitoring routes and support downstream local navigation and obstacle-avoidance control in dynamic wildlife-monitoring environments.

---

## 1. Architecture Overview

The framework follows a hierarchical navigation approach.

### Part 1: Global Route Planning

1. Environment and configuration loading.
2. Obstacle-aware A* grid pathfinding.
3. Pairwise path-distance calculation.
4. Genetic Algorithm for waypoint ordering.
5. 2-Opt local route refinement.
6. Independent route validation.
7. AirSim Integration JSON export and route visualization.

### Part 2: Local Navigation and Safety

1. Global route loading and coordinate transformation.
2. TD3-based continuous local movement control.
3. Adaptive Fuzzy Logic safety override.
4. Lightweight 3D kinematic simulation and curriculum training.
5. AirSim multirotor and sensor integration.
6. Evaluation, logging, and checkpoint management.

---

## 2. Directory Structure

```text
UAV-Navigation-in-wildlife/
│
├── backend/
│   ├── __init__.py
│   │
│   ├── global_planner/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── environment.py
│   │   ├── obstacle_manager.py
│   │   ├── waypoint_generator.py
│   │   ├── grid_pathfinder.py
│   │   ├── fitness.py
│   │   ├── genetic_algorithm.py
│   │   ├── two_opt.py
│   │   ├── route_validator.py
│   │   ├── planner_service.py
│   │   └── visualization.py
│   │
│   └── intelligent_control/
│       ├── config.py
│       ├── route_loader.py
│       ├── coordinate_transform.py
│       ├── airsim_client.py
│       ├── airsim_sensors.py
│       ├── rl_environment.py
│       ├── actor_network.py
│       ├── critic_network.py
│       ├── replay_buffer.py
│       ├── td3_agent.py
│       ├── reward_function.py
│       ├── curriculum.py
│       ├── fuzzy_safety.py
│       ├── motion_controller.py
│       ├── mission_runner.py
│       ├── evaluation.py
│       └── logging_utils.py
│
├── configs/
│   ├── default_environment.json
│   ├── controller_config.json
│   ├── safety_config.json
│   └── sample_global_route.json
│
├── models/
├── logs/
├── outputs/
│
├── tests/
│   ├── test_environment.py
│   ├── test_obstacles.py
│   ├── test_grid_pathfinder.py
│   ├── test_two_opt.py
│   ├── test_route_validator.py
│   └── test_planner.py
│
├── main.py
├── td3_main.py
├── requirements.txt
├── pytest.ini
├── INTEGRATION_GUIDE.md
└── README.md
```

---

## 3. Part 1 – Global Route Planning

### 3.1 Obstacle-Aware A* Grid Search

The environment is discretized into an occupancy grid using the configured grid resolution.

- Circular and rectangular obstacles are represented geometrically.
- Obstacles are inflated using the safety-clearance distance.
- A* searches using eight possible movement directions.
- Orthogonal movement has a cost of 1.0.
- Diagonal movement has a cost of √2.
- Diagonal corner-cutting is prevented by checking adjacent orthogonal cells.
- Pairwise paths between the start, destination, and monitoring waypoints are cached for repeated route evaluation.

### 3.2 Genetic Algorithm

The Genetic Algorithm solves the waypoint-ordering problem.

- Each chromosome represents a permutation of waypoint IDs.
- Start and destination remain fixed.
- 50% of the initial population uses Snake-Grid heuristic seeding.
- The remaining population is randomized to maintain diversity.
- Order Crossover (OX) generates valid waypoint permutations.
- Swap and inversion mutations introduce variation.
- Elitism preserves the best candidates between generations.

### 3.3 2-Opt Local Search

2-Opt improves candidate routes by reversing intermediate waypoint sequences.

- Applied every 10 generations.
- Applied to the top 20% of the population.
- Uses obstacle-aware distances when evaluating changes.
- Rejects changes that introduce collisions or unreachable segments.

### 3.4 Route Validation

An independent route validator checks:

- Start and destination endpoints.
- Monitoring waypoint coverage.
- Obstacle clearance.
- Environment boundaries.
- Path feasibility.

### 3.5 Cost Function

The objective minimizes obstacle-aware flight distance while penalizing missing or infeasible segments.

\[
\text{Total Cost} =
\text{Path Length}
+ P_{\text{missing}}N_{\text{missing}}
+ P_{\text{infeasible}}N_{\text{infeasible}}
\]

The incoming Global Planner configuration documents:

- \(P_{\text{missing}} = 100{,}000\)
- \(P_{\text{infeasible}} = 500{,}000\)

Fitness is calculated as:

\[
\text{Fitness} = \frac{1}{1+\text{Total Cost}}
\]

The Genetic Algorithm is a metaheuristic and does not guarantee the mathematical global optimum.

---

## 4. Part 2 – TD3 Local Navigation Control

The local navigation module uses Twin Delayed Deep Deterministic Policy Gradient (TD3) to generate continuous UAV movement actions.

### 4.1 TD3 Components

The implementation includes:

- Actor network.
- Twin Critic networks.
- Target Actor and Target Critic networks.
- Experience Replay Buffer.
- Target Policy Smoothing.
- Delayed Policy Updates.

The action represents continuous three-dimensional velocity:

\[
A = [v_x, v_y, v_z]
\]

### 4.2 State Representation

The local controller uses a 12-dimensional state vector.

| Indices | Information |
|---|---|
| 0–2 | Normalized relative target position |
| 3–5 | Normalized UAV velocity |
| 6 | Normalized target distance |
| 7–9 | Unit obstacle-repulsion vector |
| 10 | Normalized obstacle surface distance |
| 11 | Normalized hazard indicator |

The state representation combines target-navigation information, UAV movement, and obstacle information.

### 4.3 Training Environment

The framework includes a lightweight 3D kinematic environment and a five-stage curriculum-training process.

This supports offline training and evaluation without requiring Unreal Engine.

### 4.4 Checkpoint Management

The TD3 module supports saving and loading model checkpoints, including network and optimizer states, training progress, and configuration metadata.

The documented checkpoint location is:

```text
models/td3_wildlife_uav.pt
```

---

## 5. Adaptive Fuzzy Logic Safety

The Adaptive Fuzzy Logic (AFL) module provides a safety override for local movement commands.

It considers:

- Distance to nearby obstacles.
- Obstacle closing speed.
- Obstacle-repulsion direction.
- Lateral tangent steering.

The documented safety thresholds are:

- Safe distance: 6 metres.
- Critical distance: 2.5 metres.

The fuzzy inference system uses nine rules based on three distance categories (CRITICAL, NEAR, SAFE) and three closing-speed categories (SLOW, MODERATE, FAST).

The controller combines geometric repulsion and lateral tangent steering to modify movement commands when obstacle conditions require it.

**Note:** This heuristic safety mechanism is not a formal mathematical proof of collision avoidance.

---

## 6. AirSim Integration

The framework supports integration between the global planner and the local navigation controller.

### 6.1 Global Route Export

The Global Planner exports a validated JSON flight plan containing:

- Schema version.
- Planner identifier.
- Start and destination coordinates.
- Ordered monitoring waypoints.
- Path points.
- Route metrics.
- Validation status.

The output location is:

```text
outputs/route.json
```

### 6.2 Coordinate Transformation

The Global Planner and the AirSim controller use coordinate conventions that must be reconciled during integration.

The Part 2 coordinate transformation module handles conversion between the planner's ENU altitude-positive-up representation and AirSim's NED representation.

The exact axis mapping must remain consistent with the implementation and configuration in:

```text
backend/intelligent_control/coordinate_transform.py
```

### 6.3 AirSim Client and Sensors

The AirSim integration includes:

- Multirotor client communication.
- Safe takeoff and landing lifecycle.
- LiDAR sensor integration.
- Sensor-data processing.
- Geometric obstacle fallback.

AirSim can be used when a compatible simulator is available.

The project does not automatically spawn wildlife models in AirSim scenes; scripted objects or geometric obstacle representations can be used.

---

## 7. Installation and Setup

### 7.1 Prerequisites

The Part 2 implementation documents the following tested environment:

- Windows 10/11.
- Python 3.11.9.
- CPU-based PyTorch.
- AirSim Python client 1.8.1 for simulator integration.

The incoming Part 1 documentation also describes Ubuntu Linux with Python 3.8.10. The complete integrated project should be tested in the actual environment used by the team.

### 7.2 Create a Virtual Environment

On Windows PowerShell:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

For AirSim installations, the Part 2 setup documentation describes installing the required packages before installing AirSim without build isolation:

```powershell
python -m pip install msgpack-rpc-python
python -m pip install --no-build-isolation --no-deps airsim
```

---

## 8. Running the Global Planner

The Global Planner is executed through `main.py`.

### Default Scenario

```powershell
python main.py
```

### Custom Configuration and Output Directory

```powershell
python main.py --config configs/default_environment.json --output-dir outputs/
```

### Run Without Plots

```powershell
python main.py --no-plots
```

---

## 9. Running the TD3 Local Controller

The TD3 implementation is preserved in `td3_main.py`.

### Training

```powershell
python td3_main.py --mode train --episodes 120
```

### Dry Run

```powershell
python td3_main.py --mode dry-run --route configs/sample_global_route.json
```

### Evaluation

```powershell
python td3_main.py --mode evaluate --seeds 101 102 103 104 105
```

### AirSim Mode

```powershell
python td3_main.py --mode airsim
```

AirSim mode requires a compatible simulator instance and the appropriate settings and sensor configuration.

---

## 10. Running Tests

Run the project tests from the repository root:

```powershell
python -m pytest -v -rs
```

The incoming Global Planner documentation reports 28 deterministic tests covering:

- Environment validation and boundary constraints.
- Circular and rectangular obstacle collisions.
- Safety-clearance enforcement.
- A* obstacle detours and unreachable targets.
- Diagonal corner-cutting prevention.
- Genetic Algorithm permutation validity.
- Fixed start and destination endpoints.
- 2-Opt route refinement.
- Independent route validation.
- Same-seed reproducibility.
- AirSim JSON contract conformance.

The complete integrated project should be tested after merging both modules.

---

## 11. Limitations

The framework has the following documented limitations:

1. The project demonstrates software simulation and does not claim real-world UAV flight validation.
2. The lightweight kinematic environment does not represent every aspect of a full six-degree-of-freedom flight model.
3. The fuzzy safety controller is a heuristic mechanism, not a formal collision-avoidance guarantee.
4. Energy consumption is estimated using a proxy and does not represent measured physical battery discharge.
5. Simulated obstacle geometry does not provide camera-based wildlife perception.
6. The Genetic Algorithm does not guarantee a mathematically optimal global route.

---

## 12. Research Scope

The project combines global route optimization and local navigation control for wildlife-monitoring scenarios.

The Global Planner generates obstacle-aware routes through designated monitoring points. The local navigation module uses TD3 to generate continuous movement actions, while Adaptive Fuzzy Logic provides an additional safety override.

The AirSim integration provides a pathway for connecting the generated global route to local UAV control and simulation.

The project should be evaluated according to its implemented simulation capabilities and documented limitations.