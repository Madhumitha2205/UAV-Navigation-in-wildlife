import { describe, it, expect, beforeEach } from 'vitest'
import { useTelemetryStore } from '../store/telemetryStore'
import { generateDemoTelemetry, INITIAL_MOCK_TELEMETRY } from '../mock/mockTelemetry'

describe('Telemetry Streaming and History Handling', () => {
  beforeEach(() => {
    useTelemetryStore.getState().clearHistory()
  })

  it('updates telemetry state accurately upon packet arrival', () => {
    const store = useTelemetryStore.getState()
    const testPacket = {
      ...INITIAL_MOCK_TELEMETRY,
      position: { x: 25.4, y: 18.2, z: 17.5 },
      velocity: { vx: 2.1, vy: 1.5, vz: 0.2, speed: 2.58 },
      flight_state: 'NAVIGATING' as const,
      danger_level: 'WARNING' as const,
      safety_intervention: true,
    }

    store.updateTelemetry(testPacket)

    const updated = useTelemetryStore.getState()
    expect(updated.telemetry.position.x).toBe(25.4)
    expect(updated.telemetry.flight_state).toBe('NAVIGATING')
    expect(updated.telemetry.danger_level).toBe('WARNING')
    expect(updated.history.length).toBe(1)
  })

  it('strictly caps telemetry history to prevent memory leaks', () => {
    const store = useTelemetryStore.getState()

    // Push 45 packets
    for (let i = 0; i < 45; i++) {
      const packet = generateDemoTelemetry(i)
      store.updateTelemetry(packet)
    }

    const updated = useTelemetryStore.getState()
    // MAX_HISTORY_POINTS is set to 30
    expect(updated.history.length).toBe(30)
  })

  it('generates continuous valid demo packets along path points', () => {
    const p1 = generateDemoTelemetry(10)
    const p2 = generateDemoTelemetry(50)

    expect(p1.position).toBeDefined()
    expect(p2.position).toBeDefined()
    expect(typeof p1.velocity.speed).toBe('number')
    expect(['SAFE', 'WARNING', 'CRITICAL']).toContain(p1.danger_level)
  })
})
