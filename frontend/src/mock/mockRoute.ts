import { GlobalRoutePlan } from '../types/route'
import { EnvironmentConfig } from '../types/environment'

export const DEFAULT_ENVIRONMENT_CONFIG: EnvironmentConfig = {
  width: 80,
  height: 60,
  grid_resolution: 1.0,
  safety_clearance_m: 3.0,
  start_position: { x: 0.0, y: 0.0, z: 15.0 },
  destination: { x: 60.0, y: 50.0, z: 15.0 },
  monitoring_waypoints: [
    { id: 'WP_1', x: 20.0, y: 15.0, z: 16.0, zone_name: 'Waterhole_Alpha', priority: 1 },
    { id: 'WP_2', x: 40.0, y: 10.0, z: 18.0, zone_name: 'Ridge_Trail_East', priority: 2 },
    { id: 'WP_3', x: 45.0, y: 35.0, z: 16.0, zone_name: 'Canopy_Clearing_North', priority: 1 },
  ],
  obstacles: [
    { id: 'OBS_TREE_1', type: 'circle', x: 14.0, y: 11.0, z: 15.5, radius: 2.5 },
    { id: 'OBS_TOWER_2', type: 'circle', x: 35.0, y: 12.0, z: 17.5, radius: 2.8 },
    { id: 'OBS_CANOPY_3', type: 'circle', x: 44.0, y: 26.0, z: 16.5, radius: 2.2 },
    { id: 'OBS_RIDGE_4', type: 'rectangle', min_x: 25.0, min_y: 28.0, max_x: 32.0, max_y: 35.0, z: 16.0 },
  ],
  planning_params: {
    population_size: 100,
    max_generations: 80,
    crossover_probability: 0.85,
    mutation_probability: 0.15,
    two_opt_frequency: 5,
    two_opt_population_pct: 20,
    random_seed: 42,
  },
}

// Generate fitness progression over 80 generations
const mockFitnessHistory = Array.from({ length: 80 }, (_, i) => {
  const gen = i + 1
  // Decays from ~210 to ~88.62
  const best = 88.62 + 120 * Math.exp(-gen / 14) + (Math.sin(gen / 2) * 1.5) / (gen * 0.1 + 1)
  const avg = best + 40 * Math.exp(-gen / 25) + 5
  return {
    generation: gen,
    best_fitness: Number(best.toFixed(2)),
    avg_fitness: Number(avg.toFixed(2)),
  }
})

// Initial unoptimized straight/direct route for comparison
const initialUnoptimizedPath = [
  { x: 0.0, y: 0.0, z: 15.0 },
  { x: 40.0, y: 10.0, z: 18.0 },
  { x: 20.0, y: 15.0, z: 16.0 },
  { x: 45.0, y: 35.0, z: 16.0 },
  { x: 60.0, y: 50.0, z: 15.0 },
]

export const MOCK_GLOBAL_ROUTE: GlobalRoutePlan = {
  mission_id: 'wildlife_monitoring_corridor_01',
  planner_algorithm: 'GA_2Opt_AStar',
  coordinate_convention: {
    frame: 'ENU_ALT_UP',
    units: 'metres',
    axes: {
      x: 'East',
      y: 'North',
      z: 'Altitude_Positive_Up',
    },
  },
  validation: {
    is_valid: true,
    status: 'SUCCESS',
    collision_free: true,
    altitude_bounds_ok: true,
    planning_time_sec: 1.42,
  },
  start_position: { x: 0.0, y: 0.0, z: 15.0 },
  destination: { x: 60.0, y: 50.0, z: 15.0 },
  monitoring_waypoints: DEFAULT_ENVIRONMENT_CONFIG.monitoring_waypoints,
  intermediate_path_points: [
    { x: 0.0, y: 0.0, z: 15.0, is_monitoring: false, waypoint_id: 'START' },
    { x: 10.0, y: 8.0, z: 15.5, is_monitoring: false, waypoint_id: null },
    { x: 20.0, y: 15.0, z: 16.0, is_monitoring: true, waypoint_id: 'WP_1' },
    { x: 30.0, y: 12.5, z: 17.0, is_monitoring: false, waypoint_id: null },
    { x: 40.0, y: 10.0, z: 18.0, is_monitoring: true, waypoint_id: 'WP_2' },
    { x: 42.5, y: 22.5, z: 17.0, is_monitoring: false, waypoint_id: null },
    { x: 45.0, y: 35.0, z: 16.0, is_monitoring: true, waypoint_id: 'WP_3' },
    { x: 52.5, y: 42.5, z: 15.5, is_monitoring: false, waypoint_id: null },
    { x: 60.0, y: 50.0, z: 15.0, is_monitoring: false, waypoint_id: 'DEST' },
  ],
  static_obstacles: DEFAULT_ENVIRONMENT_CONFIG.obstacles,
  path_metrics: {
    planned_path_length_m: 88.62,
    num_monitoring_waypoints: 3,
    num_total_points: 9,
    estimated_planning_cost: 94.15,
    monitoring_coverage_pct: 100,
    minimum_obstacle_clearance_m: 3.12,
  },
  fitness_history: mockFitnessHistory,
  initial_unoptimized_path_points: initialUnoptimizedPath,
}
