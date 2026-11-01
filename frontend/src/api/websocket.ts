import { TelemetryPacket } from '../types/telemetry'
import { generateDemoTelemetry, INITIAL_MOCK_TELEMETRY } from '../mock/mockTelemetry'

export type TelemetryCallback = (telemetry: TelemetryPacket) => void
export type ConnectionStatusCallback = (status: 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' | 'ERROR') => void

export class TelemetryService {
  private ws: WebSocket | null = null
  private url: string
  private isDemoMode: boolean
  private listeners: Set<TelemetryCallback> = new Set()
  private statusListeners: Set<ConnectionStatusCallback> = new Set()
  private demoIntervalId: any = null
  private demoStep = 0
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectTimeout: any = null
  private staleCheckInterval: any = null
  private lastPacketTimestamp = 0

  constructor(url: string, isDemoMode = true) {
    this.url = url
    this.isDemoMode = isDemoMode
  }

  public setMode(isDemoMode: boolean, newUrl?: string) {
    if (newUrl) this.url = newUrl
    if (this.isDemoMode !== isDemoMode) {
      this.isDemoMode = isDemoMode
      this.disconnect()
      this.connect()
    }
  }

  public connect() {
    if (this.isDemoMode) {
      this.startDemoStream()
      return
    }

    this.stopDemoStream()
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    try {
      this.notifyStatus('RECONNECTING')
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        this.reconnectAttempts = 0
        this.notifyStatus('CONNECTED')
        this.lastPacketTimestamp = Date.now()
        this.startStaleCheck()
      }

      this.ws.onmessage = (event) => {
        try {
          const packet: TelemetryPacket = JSON.parse(event.data)
          this.lastPacketTimestamp = Date.now()
          this.notifyPacket(packet)
        } catch (err) {
          console.warn('Failed to parse telemetry packet:', err)
        }
      }

      this.ws.onclose = () => {
        this.notifyStatus('DISCONNECTED')
        this.scheduleReconnect()
      }

      this.ws.onerror = () => {
        this.notifyStatus('ERROR')
      }
    } catch (err) {
      this.notifyStatus('ERROR')
      this.scheduleReconnect()
    }
  }

  public disconnect() {
    this.stopDemoStream()
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
    if (this.staleCheckInterval) {
      clearInterval(this.staleCheckInterval)
      this.staleCheckInterval = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.notifyStatus('DISCONNECTED')
  }

  public subscribe(cb: TelemetryCallback): () => void {
    this.listeners.add(cb)
    // Send immediate initial state
    if (this.isDemoMode) {
      cb(generateDemoTelemetry(this.demoStep))
    } else {
      cb(INITIAL_MOCK_TELEMETRY)
    }
    return () => {
      this.listeners.delete(cb)
    }
  }

  public onStatusChange(cb: ConnectionStatusCallback): () => void {
    this.statusListeners.add(cb)
    cb(this.isDemoMode ? 'CONNECTED' : (this.ws?.readyState === WebSocket.OPEN ? 'CONNECTED' : 'DISCONNECTED'))
    return () => {
      this.statusListeners.delete(cb)
    }
  }

  private startDemoStream() {
    this.notifyStatus('CONNECTED')
    if (this.demoIntervalId) return

    this.demoIntervalId = setInterval(() => {
      this.demoStep += 1
      const packet = generateDemoTelemetry(this.demoStep)
      this.notifyPacket(packet)
    }, 500) // 2Hz updates in demo mode for smooth lightweight rendering
  }

  private stopDemoStream() {
    if (this.demoIntervalId) {
      clearInterval(this.demoIntervalId)
      this.demoIntervalId = null
    }
  }

  private scheduleReconnect() {
    if (this.isDemoMode) return
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 10000)
      this.reconnectTimeout = setTimeout(() => {
        this.connect()
      }, delay)
    }
  }

  private startStaleCheck() {
    if (this.staleCheckInterval) clearInterval(this.staleCheckInterval)
    this.staleCheckInterval = setInterval(() => {
      if (!this.isDemoMode && Date.now() - this.lastPacketTimestamp > 4000) {
        this.notifyStatus('ERROR')
      }
    }, 2000)
  }

  private notifyPacket(packet: TelemetryPacket) {
    for (const listener of this.listeners) {
      listener(packet)
    }
  }

  private notifyStatus(status: 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' | 'ERROR') {
    for (const listener of this.statusListeners) {
      listener(status)
    }
  }
}
