export type FlightState =
  | 'DISCONNECTED'
  | 'IDLE'
  | 'ARMED'
  | 'TAKEOFF'
  | 'NAVIGATING'
  | 'AVOIDING_OBSTACLE'
  | 'HOVERING'
  | 'RTL'
  | 'LANDING'
  | 'LANDED'
  | 'EMERGENCY'

export type DangerLevel = 'SAFE' | 'WARNING' | 'CRITICAL'

export interface TelemetryPacket {
  timestamp: number
  position: {
    x: number
    y: number
    z: number
  }
  velocity: {
    vx: number
    vy: number
    vz: number
    speed: number
  }
  target: {
    waypoint_id: string
    distance_to_target_m: number
    waypoint_index: number
    total_waypoints: number
  }
  mission_progress_pct: number
  flight_state: FlightState
  simulator_connected: boolean
  uav_armed: boolean
  api_control_enabled: boolean
  danger_level: DangerLevel
  closest_obstacle_distance_m: number
  closest_obstacle_bearing_deg?: number
  closest_obstacle_id?: string
  td3_action: [number, number, number] // [vx, vy, vz]
  final_action: [number, number, number] // [vx, vy, vz]
  safety_intervention: boolean
  safety_reason?: string
  battery_pct?: number
}

export interface TelemetryHistoryRecord {
  time: string
  speed: number
  altitude: number
  obstacle_distance: number
  progress: number
  danger_level: DangerLevel
  intervention: boolean
}
