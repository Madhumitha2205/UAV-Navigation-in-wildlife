import { TelemetryPacket, DangerLevel } from '../types/telemetry'
import { SafetyEvent } from '../types/safety'
import { MOCK_GLOBAL_ROUTE } from './mockRoute'

export const INITIAL_MOCK_TELEMETRY: TelemetryPacket = {
  timestamp: Date.now(),
  position: { x: 5.0, y: 5.0, z: 10.0, lat: 26.5775, lon: 93.1711, alt: 10.0 },
  velocity: { vx: 0.0, vy: 0.0, vz: 0.0, speed: 0.0 },
  target: {
    waypoint_id: 'WP_1',
    distance_to_target_m: 25.0,
    waypoint_index: 0,
    total_waypoints: 6,
  },
  mission_progress_pct: 0,
  flight_state: 'IDLE',
  simulator_connected: false,
  uav_armed: false,
  api_control_enabled: false,
  danger_level: 'SAFE',
  closest_obstacle_distance_m: 14.5,
  closest_obstacle_id: 'OBS_CANOPY_1',
  td3_action: [0.0, 0.0, 0.0],
  final_action: [0.0, 0.0, 0.0],
  safety_intervention: false,
  safety_reason: undefined,
  battery_pct: 98,
  fuzzy_rule_memberships: {},
}

export const MOCK_SAFETY_EVENTS: SafetyEvent[] = [
  {
    id: 'SE_101',
    timestamp: '11:42:15',
    obstacle_distance_m: 4.8,
    closest_obstacle_id: 'OBS_CANOPY_1',
    danger_level: 'WARNING',
    td3_velocity: [2.5, 1.8, 0.0],
    final_velocity: [1.8, 1.1, 0.3],
    velocity_delta: 0.98,
    intervention_status: true,
    intervention_reason: 'Proximity repulsive potential active (Warning zone < 6.0m)',
  },
  {
    id: 'SE_102',
    timestamp: '11:43:02',
    obstacle_distance_m: 2.3,
    closest_obstacle_id: 'OBS_HERD_3',
    danger_level: 'CRITICAL',
    td3_velocity: [3.2, 0.4, -0.2],
    final_velocity: [1.1, -1.2, 0.6],
    velocity_delta: 2.72,
    intervention_status: true,
    intervention_reason: 'Critical clearance boundary breach (< 2.5m) - AFL active braking and climb',
  },
]

/**
 * Simulator engine for standalone Demo Mode:
 * Advances the UAV along the route points over a step index.
 */
export function generateDemoTelemetry(step: number): TelemetryPacket {
  const points = MOCK_GLOBAL_ROUTE.intermediate_path_points
  const numSteps = 200
  const normalizedProgress = (step % numSteps) / numSteps

  const totalSegments = points.length - 1
  const segmentFloat = normalizedProgress * totalSegments
  const segIndex = Math.min(Math.floor(segmentFloat), totalSegments - 1)
  const t = segmentFloat - segIndex

  const p1 = points[segIndex]
  const p2 = points[segIndex + 1]

  const x = p1.x + (p2.x - p1.x) * t
  const y = p1.y + (p2.y - p1.y) * t
  const z = p1.z + (p2.z - p1.z) * t

  const lat1 = (p1 as any).lat ?? 26.5775
  const lon1 = (p1 as any).lon ?? 93.1711
  const lat2 = (p2 as any).lat ?? 26.6500
  const lon2 = (p2 as any).lon ?? 93.2500
  const lat = Number((lat1 + (lat2 - lat1) * t).toFixed(6))
  const lon = Number((lon1 + (lon2 - lon1) * t).toFixed(6))

  // Velocity calculation
  const dirX = p2.x - p1.x
  const dirY = p2.y - p1.y
  const mag = Math.sqrt(dirX * dirX + dirY * dirY) || 1
  const speed = 2.4 + Math.sin(step * 0.1) * 0.4
  const vx = Number(((dirX / mag) * speed).toFixed(2))
  const vy = Number(((dirY / mag) * speed).toFixed(2))
  const vz = Number(((p2.z - p1.z) * 0.2).toFixed(2))

  // Find distance to closest obstacle
  let closestDist = 999
  let closestId = 'NONE'
  for (const obs of MOCK_GLOBAL_ROUTE.static_obstacles) {
    let obsX = 0
    let obsY = 0
    if (obs.type === 'circle') {
      obsX = obs.x
      obsY = obs.y
    } else {
      obsX = (obs.min_x + obs.max_x) / 2
      obsY = (obs.min_y + obs.max_y) / 2
    }
    const d = Math.sqrt((x - obsX) ** 2 + (y - obsY) ** 2)
    if (d < closestDist) {
      closestDist = d
      closestId = obs.id
    }
  }

  let dangerLevel: DangerLevel = 'SAFE'
  let safetyIntervention = false
  let finalVx = vx
  let finalVy = vy
  let finalVz = vz
  let safetyReason: string | undefined = undefined

  if (closestDist < 2.5) {
    dangerLevel = 'CRITICAL'
    safetyIntervention = true
    finalVx = Number((vx * 0.4).toFixed(2))
    finalVy = Number((vy * 0.4).toFixed(2))
    finalVz = 0.6 // Vertical boost
    safetyReason = 'Critical distance breach (<2.5m): AFL emergency braking & climb'
  } else if (closestDist < 6.0) {
    dangerLevel = 'WARNING'
    safetyIntervention = true
    finalVx = Number((vx * 0.75).toFixed(2))
    finalVy = Number((vy * 0.75).toFixed(2))
    finalVz = 0.2
    safetyReason = 'Warning buffer active (2.5m - 6.0m): AFL velocity damping'
  }

  // Determine current waypoint
  let targetWp = 'WP_1'
  let targetDist = 15.0
  const wpIndex = Math.min(
    Math.floor(normalizedProgress * MOCK_GLOBAL_ROUTE.monitoring_waypoints.length),
    MOCK_GLOBAL_ROUTE.monitoring_waypoints.length - 1
  )
  const activeWp = MOCK_GLOBAL_ROUTE.monitoring_waypoints[wpIndex]
  if (activeWp) {
    targetWp = activeWp.id
    targetDist = Math.max(0, (1 - normalizedProgress) * 45)
  }

  return {
    timestamp: Date.now(),
    position: {
      x: Number(x.toFixed(2)),
      y: Number(y.toFixed(2)),
      z: Number(z.toFixed(2)),
      lat,
      lon,
      alt: Number(z.toFixed(2)),
    },
    velocity: {
      vx,
      vy,
      vz,
      speed: Number(speed.toFixed(2)),
    },
    target: {
      waypoint_id: targetWp,
      distance_to_target_m: Number(targetDist.toFixed(1)),
      waypoint_index: wpIndex,
      total_waypoints: MOCK_GLOBAL_ROUTE.monitoring_waypoints.length,
    },
    mission_progress_pct: Math.min(100, Math.round(normalizedProgress * 100)),
    flight_state: normalizedProgress > 0.95 ? 'LANDING' : safetyIntervention ? 'AVOIDING_OBSTACLE' : 'NAVIGATING',
    simulator_connected: true,
    uav_armed: true,
    api_control_enabled: true,
    danger_level: dangerLevel,
    closest_obstacle_distance_m: Number(closestDist.toFixed(2)),
    closest_obstacle_id: closestId,
    td3_action: [vx, vy, vz],
    final_action: [finalVx, finalVy, finalVz],
    safety_intervention: safetyIntervention,
    safety_reason: safetyReason,
    battery_pct: Math.max(10, Math.round(98 - normalizedProgress * 22)),
    fuzzy_rule_memberships: {
      R1: closestDist < 2.5 ? 0.95 : 0.0,
      R4: closestDist < 6.0 && closestDist >= 2.5 ? 0.75 : 0.0,
      R8: closestDist >= 6.0 ? 1.0 : 0.0,
    },
  }
}
