import { controlClient } from './axiosClient'

export interface SimulationStatusResponse {
  simulator_connected: boolean
  simulator_version?: string
  uav_armed: boolean
  api_control_enabled: boolean
  active_mission_id?: string
  flight_state: string
  is_demo: boolean
}

export const controlApi = {
  async getSimulationStatus(isDemoMode: boolean = true): Promise<SimulationStatusResponse> {
    if (isDemoMode) {
      return {
        simulator_connected: true,
        simulator_version: 'AirSim-v1.8.1-UE4-Simulated',
        uav_armed: true,
        api_control_enabled: true,
        active_mission_id: 'wildlife_monitoring_corridor_01',
        flight_state: 'NAVIGATING',
        is_demo: true,
      }
    }
    const response = await controlClient.get<SimulationStatusResponse>('/api/simulation/status')
    return { ...response.data, is_demo: false }
  },

  async connectSimulator(isDemoMode: boolean = true) {
    if (isDemoMode) {
      return { success: true, message: 'Simulated AirSim connection established [DEMO]' }
    }
    const response = await controlClient.post('/api/simulation/connect')
    return response.data
  },

  async disconnectSimulator(isDemoMode: boolean = true) {
    if (isDemoMode) {
      return { success: true, message: 'Simulated AirSim disconnected [DEMO]' }
    }
    const response = await controlClient.post('/api/simulation/disconnect')
    return response.data
  },

  async startMission(missionId: string, isDemoMode: boolean = true) {
    if (isDemoMode) {
      return { success: true, mission_id: missionId, message: 'Demo mission started' }
    }
    const response = await controlClient.post('/api/mission/start', { mission_id: missionId })
    return response.data
  },

  async pauseMission(isDemoMode: boolean = true) {
    if (isDemoMode) {
      return { success: true, message: 'Demo mission paused' }
    }
    const response = await controlClient.post('/api/mission/pause')
    return response.data
  },

  async resumeMission(isDemoMode: boolean = true) {
    if (isDemoMode) {
      return { success: true, message: 'Demo mission resumed' }
    }
    const response = await controlClient.post('/api/mission/resume')
    return response.data
  },

  async stopMission(isDemoMode: boolean = true) {
    if (isDemoMode) {
      return { success: true, message: 'Demo mission aborted safely' }
    }
    const response = await controlClient.post('/api/mission/stop')
    return response.data
  },

  async returnToLand(isDemoMode: boolean = true) {
    if (isDemoMode) {
      return { success: true, message: 'Return to Launch initiated [DEMO]' }
    }
    const response = await controlClient.post('/api/mission/rtl')
    return response.data
  },

  async landUAV(isDemoMode: boolean = true) {
    if (isDemoMode) {
      return { success: true, message: 'Immediate Landing initiated [DEMO]' }
    }
    const response = await controlClient.post('/api/mission/land')
    return response.data
  },
}
