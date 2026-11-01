import { useState, useEffect } from 'react'
import { useSettingsStore } from '../store/settingsStore'
import { controlApi } from '../api/controlApi'
import { BackendConnectionStatus } from '../types/mission'

export function useConnectionStatus(): BackendConnectionStatus {
  const { demoMode } = useSettingsStore()
  const [status, setStatus] = useState<BackendConnectionStatus>({
    global_planner_api: demoMode ? 'ONLINE' : 'CHECKING',
    control_api: demoMode ? 'ONLINE' : 'CHECKING',
    airsim_simulation: demoMode ? 'CONNECTED' : 'STANDBY',
    websocket_telemetry: demoMode ? 'CONNECTED' : 'DISCONNECTED',
    demo_mode: demoMode,
  })

  useEffect(() => {
    if (demoMode) {
      setStatus({
        global_planner_api: 'ONLINE',
        control_api: 'ONLINE',
        airsim_simulation: 'CONNECTED',
        websocket_telemetry: 'CONNECTED',
        demo_mode: true,
      })
      return
    }

    let isMounted = true
    const checkLiveStatus = async () => {
      try {
        const sim = await controlApi.getSimulationStatus(false)
        if (isMounted) {
          setStatus({
            global_planner_api: 'ONLINE',
            control_api: 'ONLINE',
            airsim_simulation: sim.simulator_connected ? 'CONNECTED' : 'DISCONNECTED',
            websocket_telemetry: 'CONNECTED',
            demo_mode: false,
          })
        }
      } catch {
        if (isMounted) {
          setStatus({
            global_planner_api: 'OFFLINE',
            control_api: 'OFFLINE',
            airsim_simulation: 'DISCONNECTED',
            websocket_telemetry: 'DISCONNECTED',
            demo_mode: false,
          })
        }
      }
    }

    checkLiveStatus()
    const timer = setInterval(checkLiveStatus, 10000)

    return () => {
      isMounted = false
      clearInterval(timer)
    }
  }, [demoMode])

  return status
}
