export type MissionStatus =
  | 'CONFIGURING'
  | 'PLANNED'
  | 'EXECUTING'
  | 'PAUSED'
  | 'COMPLETED'
  | 'FAILED'
  | 'ABORTED'

export interface ActivityEvent {
  id: string
  timestamp: string
  title: string
  description: string
  category: 'MISSION' | 'PLANNER' | 'SIMULATION' | 'SAFETY' | 'SYSTEM'
  severity: 'info' | 'success' | 'warning' | 'danger'
}

export interface MissionOverviewMetrics {
  total_missions: number
  completed_missions: number
  current_mission_status: MissionStatus
  current_altitude_m: number
  current_speed_mps: number
  monitoring_coverage_pct: number
  collision_count: number
  fuzzy_intervention_count: number
  is_demo: boolean
}

export interface BackendConnectionStatus {
  global_planner_api: 'ONLINE' | 'OFFLINE' | 'CHECKING'
  control_api: 'ONLINE' | 'OFFLINE' | 'CHECKING'
  airsim_simulation: 'CONNECTED' | 'DISCONNECTED' | 'ERROR' | 'STANDBY'
  websocket_telemetry: 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING'
  demo_mode: boolean
}
