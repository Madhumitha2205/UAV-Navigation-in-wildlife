import { Point3D, MonitoringWaypoint, StaticObstacle } from './environment'

export interface IntermediatePathPoint extends Point3D {
  is_monitoring: boolean
  waypoint_id: string | null
}

export interface RouteValidation {
  is_valid: boolean
  status: 'SUCCESS' | 'FAILED' | 'PARTIAL' | 'PENDING'
  collision_free: boolean
  altitude_bounds_ok?: boolean
  planning_time_sec: number
  validation_errors?: string[]
}

export interface CoordinateConvention {
  frame: 'ENU_ALT_UP' | 'NED' | string
  units: 'metres' | string
  axes: {
    x: string
    y: string
    z: string
  }
}

export interface PathMetrics {
  planned_path_length_m: number
  num_monitoring_waypoints: number
  num_total_points: number
  estimated_planning_cost?: number
  monitoring_coverage_pct?: number
  minimum_obstacle_clearance_m?: number
}

export interface FitnessGenerationRecord {
  generation: number
  best_fitness: number
  avg_fitness?: number
}

export interface GlobalRoutePlan {
  mission_id: string
  planner_algorithm: string
  coordinate_convention: CoordinateConvention
  validation: RouteValidation
  start_position: Point3D
  destination: Point3D
  monitoring_waypoints: MonitoringWaypoint[]
  intermediate_path_points: IntermediatePathPoint[]
  static_obstacles: StaticObstacle[]
  path_metrics: PathMetrics
  fitness_history?: FitnessGenerationRecord[]
  initial_unoptimized_path_points?: Point3D[]
}
