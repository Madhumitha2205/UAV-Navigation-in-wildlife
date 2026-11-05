import { GlobalRoutePlan } from '../types/route'
import { EnvironmentConfig } from '../types/environment'

export const DEFAULT_ENVIRONMENT_CONFIG: EnvironmentConfig = {
  width: 80,
  height: 60,
  grid_resolution: 1.0,
  safety_clearance_m: 2.0,
  start_position: { x: 5.0, y: 5.0, z: 10.0, lat: 26.5775, lon: 93.1711 },
  destination: { x: 60.0, y: 50.0, z: 10.0, lat: 26.6500, lon: 93.2500 },
  monitoring_waypoints: [
    { id: 'WP_1', x: 15.0, y: 30.0, z: 10.0, lat: 26.5890, lon: 93.1820, zone_name: 'Waterhole_Alpha', priority: 1 },
    { id: 'WP_2', x: 35.0, y: 20.0, z: 10.0, lat: 26.5980, lon: 93.1950, zone_name: 'Grazing_Plain_Bravo', priority: 2 },
    { id: 'WP_3', x: 45.0, y: 35.0, z: 10.0, lat: 26.6150, lon: 93.2200, zone_name: 'River_Crossing_Charlie', priority: 1 },
    { id: 'WP_4', x: 55.0, y: 45.0, z: 10.0, lat: 26.6320, lon: 93.2350, zone_name: 'Canopy_Edge_Delta', priority: 1 },
  ],
  obstacles: [
    { id: 'OBS_CANOPY_1', type: 'circle', x: 25.0, y: 25.0, z: 10.0, radius: 6.0, lat: 26.6100, lon: 93.2050, radius_m: 250 },
    { id: 'OBS_RIDGE_2', type: 'rectangle', min_x: 35.0, min_y: 28.0, max_x: 42.0, max_y: 35.0, z: 10.0, lat: 26.6250, lon: 93.2250 },
    { id: 'OBS_HERD_3', type: 'circle', x: 20.0, y: 40.0, z: 10.0, radius: 5.0, lat: 26.6200, lon: 93.1900, radius_m: 200 },
  ],
  planning_params: {
    population_size: 80,
    max_generations: 80,
    crossover_probability: 0.8,
    mutation_probability: 0.02,
    two_opt_frequency: 10,
    two_opt_population_pct: 0.2,
    random_seed: 42,
  },
}

// Generate fitness progression over generations
const mockFitnessHistory = Array.from({ length: 50 }, (_, i) => {
  const gen = i + 1
  const best = 294.85 + 85 * Math.exp(-gen / 10) + (Math.sin(gen / 3) * 2.0)
  const avg = best + 35 * Math.exp(-gen / 15) + 3
  return {
    generation: gen,
    best_fitness: Number(best.toFixed(2)),
    avg_fitness: Number(avg.toFixed(2)),
  }
})

// Initial unoptimized straight/direct route for comparison
const initialUnoptimizedPath = [
  { x: 5.0, y: 5.0, z: 10.0, lat: 26.5775, lon: 93.1711 },
  { x: 15.0, y: 30.0, z: 10.0, lat: 26.5890, lon: 93.1820 },
  { x: 35.0, y: 20.0, z: 10.0, lat: 26.5980, lon: 93.1950 },
  { x: 45.0, y: 35.0, z: 10.0, lat: 26.6150, lon: 93.2200 },
  { x: 55.0, y: 45.0, z: 10.0, lat: 26.6320, lon: 93.2350 },
  { x: 60.0, y: 50.0, z: 10.0, lat: 26.6500, lon: 93.2500 },
]

export const MOCK_GLOBAL_ROUTE: GlobalRoutePlan = {
  mission_id: 'wildlife_monitoring_kaziranga_01',
  planner_algorithm: 'GA_2OPT_ASTAR',
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
    planning_time_sec: 0.455,
  },
  start_position: DEFAULT_ENVIRONMENT_CONFIG.start_position,
  destination: DEFAULT_ENVIRONMENT_CONFIG.destination,
  monitoring_waypoints: DEFAULT_ENVIRONMENT_CONFIG.monitoring_waypoints,
  intermediate_path_points: [
    { x: 5.0, y: 5.0, z: 10.0, lat: 26.5775, lon: 93.1711, is_monitoring: false, waypoint_id: 'START' },
    { x: 15.0, y: 30.0, z: 10.0, lat: 26.5890, lon: 93.1820, is_monitoring: true, waypoint_id: 'WP_1' },
    { x: 35.0, y: 20.0, z: 10.0, lat: 26.5980, lon: 93.1950, is_monitoring: true, waypoint_id: 'WP_2' },
    { x: 45.0, y: 35.0, z: 10.0, lat: 26.6150, lon: 93.2200, is_monitoring: true, waypoint_id: 'WP_3' },
    { x: 55.0, y: 45.0, z: 10.0, lat: 26.6320, lon: 93.2350, is_monitoring: true, waypoint_id: 'WP_4' },
    { x: 60.0, y: 50.0, z: 10.0, lat: 26.6500, lon: 93.2500, is_monitoring: false, waypoint_id: 'DEST' },
  ],
  static_obstacles: DEFAULT_ENVIRONMENT_CONFIG.obstacles,
  path_metrics: {
    planned_path_length_m: 294.85,
    num_monitoring_waypoints: 4,
    num_total_points: 6,
    estimated_planning_cost: 294.85,
    monitoring_coverage_pct: 100,
    minimum_obstacle_clearance_m: 2.25,
  },
  fitness_history: mockFitnessHistory,
  initial_unoptimized_path_points: initialUnoptimizedPath,
}
