# Intelligent Hierarchical UAV Navigation Framework: Global Route Planning Backend

Part of the research project:
> *"An Intelligent Hierarchical UAV Navigation Framework for Safe and Energy-Efficient Wildlife Monitoring in Dynamic Environments"*

This repository contains the independent **Global Route Planning and Environment Backend** (Part 1). It computes global obstacle-aware, safety-cleared surveillance trajectories visiting designated wildlife monitoring points using a **hybrid Permutation Genetic Algorithm (GA)**, **2-Opt local search refinement**, and **obstacle-aware A* pathfinding on an occupancy grid**.

The output is exported to an **AirSim Integration JSON contract**, allowing downstream modules (AirSim 3D simulation, TD3 local movement controller, Adaptive Fuzzy Logic safety override) to ingest and execute the global flight plan without inter-module coupling.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |      Environment & Config JSON       |
                      |  (Start, Dest, Waypoints, Obstacles)  |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |        Obstacle-Aware A* Grid         |
                      |  (Clearance Inflation, No Corner Cut) |
                      |    Pairwise Path Distance Matrix      |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |      Permutation Genetic Algorithm    |
                      |   - 50% Snake-Grid Population Seeding |
                      |   - Order Crossover (OX)              |
                      |   - Swap / Inversion Mutation         |
                      |   - Elitism & Convergence Patience    |
                      +---------------------------------------+
                                          |
                                          v (Every 10 Gens on Top 20%)
                      +---------------------------------------+
                      |         2-Opt Local Optimizer         |
                      |    (Subsequence Reversal & Detour)    |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |     Independent Route Validator       |
                      |  (Endpoints, Clearance, Bounds, Path) |
                      +---------------------------------------+
                                          |
                     +--------------------+--------------------+
                     |                                         |
                     v                                         v
        +-------------------------+               +-------------------------+
        | AirSim Integration JSON |               |   Visualization Plots   |
        |  `outputs/route.json`   |               | `outputs/*.png` (Maps)  |
        +-------------------------+               +-------------------------+
```

---

## Directory Structure

```
backend/
  __init__.py
  global_planner/
    __init__.py
    config.py                 # Dataclasses and JSON config validation
    environment.py            # 2D continuous environment model and coordinate bounds
    obstacle_manager.py       # Exact geometric obstacles (Circle, Rectangle) & clearance
    waypoint_generator.py     # Lawnmower/Snake-Grid coverage and heuristic seeding
    grid_pathfinder.py        # 8-connected A* search with corner-cutting prevention
    fitness.py                # Pairwise distance matrix & penalty-based cost evaluation
    genetic_algorithm.py      # Permutation GA with OX crossover, mutation, elitism
    two_opt.py                # 2-Opt local search edge-reversal optimizer
    route_validator.py        # Independent safety, boundary, and coverage validator
    planner_service.py        # Public API facade & AirSim JSON contract exporter
    visualization.py          # Publication-ready Matplotlib route and convergence plots
configs/
  default_environment.json   # Benchmark scenario with circular and rectangular obstacles
tests/
  test_environment.py       # Environment validation and boundary constraints
  test_obstacles.py         # Collision detection and clearance buffer tests
  test_grid_pathfinder.py   # A* detours, corner-cutting prevention, unreachable targets
  test_two_opt.py           # 2-Opt crossing elimination and feasibility preservation
  test_route_validator.py   # Rejection of invalid, colliding, or incomplete paths
  test_planner.py           # End-to-end integration, reproducibility, and JSON contract
outputs/                    # Generated flight plans and trajectory plots
main.py                     # Command-line entry point
requirements.txt            # Minimal CPU dependencies (numpy, matplotlib, pytest)
README.md                   # Comprehensive technical documentation
.gitignore                  # Git hygiene configuration
```

---

## Installation & Setup

### Prerequisites
- Ubuntu Linux (tested and verified on Ubuntu with Python 3.8.10)
- `python3` and `python3-venv`

### Virtual Environment Setup
From the repository root directory:

```bash
# 1. Create a dedicated virtual environment
python3 -m venv .venv

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Upgrade pip and install minimal dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## How to Run the Planner

### Default Scenario
Execute the global planner using the default wildlife monitoring configuration:

```bash
python main.py
```

### Custom Configuration & Output Directory
You can specify custom environment configurations and target output folders:

```bash
python main.py --config configs/default_environment.json --output-dir outputs/
```

### Run Without Plots (Headless / Faster)
```bash
python main.py --no-plots
```

---

## How to Run Tests

All unit, integration, and contract tests are automated with `pytest`:

```bash
pytest -v
```

Running tests from within the repository root runs 28 deterministic tests covering:
- Boundary checks and environment validation
- Circular and rectangular obstacle collisions
- Exact safety clearance buffer enforcement
- A* obstacle detours and unreachable target detection
- Prevention of diagonal corner cutting
- Genetic Algorithm permutation validity (OX crossover & mutation)
- Fixed start and destination endpoints
- 2-Opt deterministic untangling of inefficient routes
- Independent route validation and missing-waypoint rejection
- Same-seed reproducibility
- AirSim JSON schema contract conformance

---

## Algorithm Details (In Simple Language)

### 1. Obstacle-Aware A* Grid Search (`grid_pathfinder.py`)
- Discretizes the 2D world into an occupancy grid of resolution `grid_resolution`.
- Obstacles (circles, rectangles, dynamic snapshots) are inflated by `safety_clearance`. Any grid cell touching this inflated zone is marked blocked.
- Moves in 8 directions (orthogonal cost $1.0$, diagonal cost $\sqrt{2}$).
- **Corner-Cutting Prevention**: When moving diagonally from cell $(r, c)$ to $(r+\Delta r, c+\Delta c)$, both adjacent orthogonal cells $(r+\Delta r, c)$ and $(r, c+\Delta c)$ must be free. This guarantees that the UAV never grazes or clips the sharp corner of an obstacle.
- All pairwise paths between Start, Destination, and all Waypoints are cached in an $(N+2) \times (N+2)$ lookup matrix. Evaluating a new waypoint order during GA evolution takes nanoseconds because no new A* searches are needed.

### 2. Genetic Algorithm (`genetic_algorithm.py`)
- Solves the Traveling Salesperson Problem with Obstacles (TSP-O): finding the optimal visit order for all required wildlife monitoring waypoints.
- A **chromosome** is a permutation of waypoint IDs $[w_0, w_1, \dots, w_{N-1}]$. Start and Destination remain fixed endpoints.
- **Population Seeding**: 50% of the initial population is seeded using the **Snake-Grid spatial heuristic** (which groups waypoints by latitude/Y-coordinate and alternates horizontal traversal), giving the GA an immediate, geometrically sensible starting point. The remaining 50% is randomized for diversity.
- **Order Crossover (OX)**: Selects a subsegment from Parent 1, copies it into the offspring, and fills remaining slots with genes from Parent 2 in wrap-around order. This mathematically guarantees that every waypoint is visited exactly once with no duplicates.
- **Mutation**: Randomly swaps two waypoints or inverts a subsequence.
- **Elitism**: Top individuals are directly carried over into subsequent generations to preserve best solutions.

### 3. 2-Opt Local Search (`two_opt.py`)
- Periodically applied every 10 generations to the top 20% of the GA population.
- Selects two route edges and reverses the intermediate sequence of waypoints.
- Eliminates route self-intersections and loops.
- Re-evaluates using true obstacle-aware distances and strictly rejects any move that introduces collisions or unreachability.

---

## Cost Function & Fitness (`fitness.py`)

The objective function minimizes total obstacle-aware flight distance while enforcing constraints:

$$\text{Total Cost} = \text{Path Length (m)} + P_{\text{missing}} \times N_{\text{missing}} + P_{\text{infeasible}} \times N_{\text{infeasible}}$$

Where:
- $\text{Path Length}$: Sum of A* path lengths connecting $\text{Start} \rightarrow w_{\pi_0} \rightarrow w_{\pi_1} \dots \rightarrow \text{Destination}$.
- $P_{\text{missing}} = 100,000$: Penalty per missing mandatory monitoring waypoint.
- $P_{\text{infeasible}} = 500,000$: Penalty if any segment has no collision-free path around obstacles.

Fitness for selection ranking is:

$$\text{Fitness} = \frac{1.0}{1.0 + \text{Total Cost}}$$

> **Limitations**: The GA is a metaheuristic search; it finds high-quality, collision-free paths rapidly but does not guarantee the mathematical global optimum. Energy consumption in real flight depends on wind, altitude changes, and aerodynamics, which are evaluated downstream in AirSim.

---

## Configuration Reference (`configs/default_environment.json`)

| Field | Type | Description |
|---|---|---|
| `environment.x_min`, `x_max` | float | Horizontal map bounds in meters |
| `environment.y_min`, `y_max` | float | Vertical map bounds in meters |
| `environment.default_altitude`| float | Default flight altitude metadata in meters (positive up) |
| `environment.safety_clearance`| float | Buffer distance around all obstacles (meters) |
| `environment.grid_resolution` | float | Discretization cell size for A* pathfinding (meters) |
| `environment.start` | object | Start coordinate `{x, y, altitude}` |
| `environment.destination` | object | Destination coordinate `{x, y, altitude}` |
| `environment.circular_obstacles` | list | Circular obstacles `[{id, x, y, radius}]` |
| `environment.rectangular_obstacles`| list | Axis-aligned boxes `[{id, x_min, x_max, y_min, y_max}]` |
| `environment.dynamic_obstacles`| list | Dynamic wildlife snapshots treated as static obstacles for run |
| `environment.monitoring_waypoints` | list | Target waypoints `[{id, x, y, altitude, importance_weight, is_mandatory}]` |
| `genetic_algorithm.population_size` | int | Number of candidate chromosomes per generation (e.g. 80) |
| `genetic_algorithm.max_generations` | int | Maximum evolution iterations (e.g. 200) |
| `genetic_algorithm.crossover_probability` | float | Probability of applying OX crossover (e.g. 0.8) |
| `genetic_algorithm.mutation_probability` | float | Probability of mutation (e.g. 0.02) |
| `genetic_algorithm.snake_grid_init_ratio`| float | Proportion of population initialized with Snake heuristic (0.50) |
| `genetic_algorithm.two_opt_frequency` | int | Generation interval to trigger 2-Opt on top candidates (10) |
| `genetic_algorithm.two_opt_candidate_ratio`| float | Top fraction of population receiving 2-Opt (0.20) |
| `genetic_algorithm.random_seed` | int | Integer seed for deterministic, reproducible planning |

---

## AirSim Integration Contract

The planner exports a validated JSON flight plan adhering to the following schema:

```json
{
  "schema_version": "1.0",
  "planner": "GA_2OPT_ASTAR",
  "status": "success",
  "coordinate_frame": "planner_xy_altitude_up",
  "start": {"x": 5.0, "y": 5.0, "altitude": 10.0},
  "destination": {"x": 95.0, "y": 95.0, "altitude": 10.0},
  "ordered_monitoring_waypoints": [
    {
      "order": 1,
      "id": "waterhole_alpha",
      "x": 15.0,
      "y": 30.0,
      "altitude": 10.0,
      "importance_weight": 1.2
    }
  ],
  "path_points": [
    {"point_index": 0, "x": 5.0, "y": 5.0, "altitude": 10.0},
    {"point_index": 1, "x": 6.0, "y": 6.0, "altitude": 10.0}
  ],
  "metrics": {
    "path_length": 294.85,
    "coverage_percentage": 100.0,
    "visited_waypoints": 6,
    "required_waypoints": 6,
    "collision_count": 0,
    "minimum_obstacle_clearance": 2.25,
    "planning_time_seconds": 1.10,
    "generations_completed": 50,
    "two_opt_improvements": 0
  },
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  }
}
```

### Coordinate Frame Conversion for AirSim Teammate
- **Planner Convention**: Right-handed 2D Euclidean with altitude positive-up: $(X, Y, Z_{\text{alt}})$.
- **AirSim Convention**: North-East-Down (NED): $(X_{\text{ned}}, Y_{\text{ned}}, Z_{\text{ned}})$.
- **Conversion Formula**:
  $$X_{\text{airsim}} = X_{\text{planner}}$$
  $$Y_{\text{airsim}} = Y_{\text{planner}}$$
  $$Z_{\text{airsim}} = -Z_{\text{alt, planner}}$$

---

## Troubleshooting & FAQ

1. **`ModuleNotFoundError: No module named 'backend'`**:
   Ensure `pytest.ini` is present or set `PYTHONPATH=.` when invoking commands.
2. **`Matplotlib / cache directory permission warnings`**:
   The code automatically sets `MPLCONFIGDIR=/tmp/mpl_cache` and uses the headless `Agg` backend to avoid display or permission errors on headless servers.
3. **Infeasible Route Reported**:
   If `status` is `"failure"`, inspect the `validation.errors` list. Common causes are waypoints placed inside obstacles or tight corridors smaller than `2 * safety_clearance`.