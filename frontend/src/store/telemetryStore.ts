import { create } from 'zustand'
import { TelemetryPacket, TelemetryHistoryRecord } from '../types/telemetry'
import { INITIAL_MOCK_TELEMETRY } from '../mock/mockTelemetry'

interface TelemetryState {
  telemetry: TelemetryPacket
  history: TelemetryHistoryRecord[]
  connectionStatus: 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' | 'ERROR'
  isArmed: boolean
  updateTelemetry: (packet: TelemetryPacket) => void
  setConnectionStatus: (status: 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' | 'ERROR') => void
  clearHistory: () => void
}

const MAX_HISTORY_POINTS = 30

export const useTelemetryStore = create<TelemetryState>((set) => ({
  telemetry: INITIAL_MOCK_TELEMETRY,
  history: [],
  connectionStatus: 'CONNECTED',
  isArmed: true,

  updateTelemetry: (packet) =>
    set((state) => {
      const record: TelemetryHistoryRecord = {
        time: new Date(packet.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        speed: packet.velocity.speed,
        altitude: packet.position.z,
        obstacle_distance: packet.closest_obstacle_distance_m,
        progress: packet.mission_progress_pct,
        danger_level: packet.danger_level,
        intervention: packet.safety_intervention,
      }

      const updatedHistory = [...state.history, record]
      if (updatedHistory.length > MAX_HISTORY_POINTS) {
        updatedHistory.shift()
      }

      return {
        telemetry: packet,
        isArmed: packet.uav_armed,
        history: updatedHistory,
      }
    }),

  setConnectionStatus: (status) => set({ connectionStatus: status }),
  clearHistory: () => set({ history: [] }),
}))
