import { useEffect, useRef } from 'react'
import { TelemetryService } from '../api/websocket'
import { useTelemetryStore } from '../store/telemetryStore'
import { useSettingsStore } from '../store/settingsStore'

let telemetryServiceInstance: TelemetryService | null = null

export function getTelemetryService(wsUrl: string, isDemo: boolean): TelemetryService {
  if (!telemetryServiceInstance) {
    telemetryServiceInstance = new TelemetryService(wsUrl, isDemo)
  } else {
    telemetryServiceInstance.setMode(isDemo, wsUrl)
  }
  return telemetryServiceInstance
}

export function useTelemetry() {
  const { wsUrl, demoMode } = useSettingsStore()
  const { telemetry, history, connectionStatus, updateTelemetry, setConnectionStatus } =
    useTelemetryStore()

  const serviceRef = useRef<TelemetryService | null>(null)

  useEffect(() => {
    const service = getTelemetryService(wsUrl, demoMode)
    serviceRef.current = service

    const unsubTelemetry = service.subscribe((packet) => {
      updateTelemetry(packet)
    })

    const unsubStatus = service.onStatusChange((status) => {
      setConnectionStatus(status)
    })

    service.connect()

    return () => {
      unsubTelemetry()
      unsubStatus()
    }
  }, [wsUrl, demoMode, updateTelemetry, setConnectionStatus])

  return {
    telemetry,
    history,
    connectionStatus,
    isDemo: demoMode,
  }
}
