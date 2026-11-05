export interface Point3D {
  x: number
  y: number
  z: number
  lat?: number
  lon?: number
}

export interface MonitoringWaypoint extends Point3D {
  id: string
  zone_name: string
  priority: number // 1: High, 2: Medium, 3: Low
}

export interface CircularObstacle {
  id: string
  type: 'circle'
  x: number
  y: number
  z: number
  radius: number
  lat?: number
  lon?: number
  radius_m?: number
}

export interface RectangularObstacle {
  id: string
  type: 'rectangle'
  min_x: number
  min_y: number
  max_x: number
  max_y: number
  z: number
  lat?: number
  lon?: number
}

export type StaticObstacle = CircularObstacle | RectangularObstacle

export interface GAPlanningParameters {
  population_size: number
  max_generations: number
  crossover_probability: number
  mutation_probability: number
  two_opt_frequency: number
  two_opt_population_pct: number
  random_seed?: number
}

export interface EnvironmentConfig {
  width: number
  height: number
  grid_resolution: number
  safety_clearance_m: number
  start_position: Point3D
  destination: Point3D
  monitoring_waypoints: MonitoringWaypoint[]
  obstacles: StaticObstacle[]
  planning_params: GAPlanningParameters
}
