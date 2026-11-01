import { DangerLevel } from './telemetry'

export interface SafetyThresholds {
  safe_distance_m: number
  critical_distance_m: number
  collision_radius_m: number
  max_repulsion_speed_mps: number
  braking_gain: number
  vertical_clearance_boost_mps: number
  intervention_threshold: number
  emergency_brake_threshold: number
}

export interface SafetyEvent {
  id: string
  timestamp: string
  obstacle_distance_m: number
  closest_obstacle_id?: string
  danger_level: DangerLevel
  td3_velocity: [number, number, number]
  final_velocity: [number, number, number]
  velocity_delta: number
  intervention_status: boolean
  intervention_reason: string
}

export interface NearbyObstacleReading {
  id: string
  type: string
  distance_m: number
  bearing_deg: number
  relative_altitude_m: number
  danger_level: DangerLevel
  sensor_status: 'ACTIVE' | 'DEGRADED' | 'FAULT'
}
