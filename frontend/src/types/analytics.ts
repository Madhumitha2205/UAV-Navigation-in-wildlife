export interface MissionAnalyticsSummary {
  experiment_id: string
  mission_id: string
  execution_date: string
  completion_rate_pct: number
  planned_route_length_m: number
  actual_travelled_distance_m: number
  monitoring_coverage_pct: number
  collision_count: number
  min_obstacle_distance_m: number
  execution_duration_sec: number
  control_smoothness_rms_jerk: number
  fuzzy_intervention_count: number
  fuzzy_intervention_rate_pct: number
  estimated_energy_proxy_joules: number
  is_demo: boolean
}

export type ExperimentConfiguration = 'A_BASELINE' | 'B_TD3_RAW' | 'C_TD3_FUZZY'

export interface ConfigurationResult {
  config_id: ExperimentConfiguration
  config_name: string
  description: string
  completion_rate_pct: number
  travelled_distance_m: number
  collision_count: number
  monitoring_coverage_pct: number
  control_smoothness_rms_jerk: number
  execution_time_sec: number
  fuzzy_interventions: number
  estimated_energy_proxy_joules: number
  success: boolean
}

export interface ExperimentTrial {
  trial_id: string
  scenario_name: string
  seed: number
  config_a: ConfigurationResult
  config_b: ConfigurationResult
  config_c: ConfigurationResult
}
