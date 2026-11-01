import { describe, it, expect, beforeEach } from 'vitest'
import { useMissionStore } from '../store/missionStore'

describe('Mission Store State Management', () => {
  beforeEach(() => {
    useMissionStore.getState().resetToDefaults()
  })

  it('initializes with default environment configuration', () => {
    const state = useMissionStore.getState()
    expect(state.environmentConfig.width).toBe(80)
    expect(state.environmentConfig.height).toBe(60)
    expect(state.environmentConfig.monitoring_waypoints.length).toBeGreaterThan(0)
    expect(state.currentRoutePlan).not.toBeNull()
  })

  it('adds, updates, and deletes monitoring waypoints correctly', () => {
    const store = useMissionStore.getState()
    const initialCount = store.environmentConfig.monitoring_waypoints.length

    // Add
    const newWp = {
      id: 'WP_TEST_99',
      zone_name: 'Test_Canopy',
      x: 33.5,
      y: 44.2,
      z: 16.0,
      priority: 1,
    }
    store.addWaypoint(newWp)

    let updatedWaypoints = useMissionStore.getState().environmentConfig.monitoring_waypoints
    expect(updatedWaypoints.length).toBe(initialCount + 1)
    expect(updatedWaypoints.find((w) => w.id === 'WP_TEST_99')?.zone_name).toBe('Test_Canopy')

    // Update
    useMissionStore.getState().updateWaypoint('WP_TEST_99', { zone_name: 'Renamed_Zone' })
    updatedWaypoints = useMissionStore.getState().environmentConfig.monitoring_waypoints
    expect(updatedWaypoints.find((w) => w.id === 'WP_TEST_99')?.zone_name).toBe('Renamed_Zone')

    // Remove
    useMissionStore.getState().removeWaypoint('WP_TEST_99')
    updatedWaypoints = useMissionStore.getState().environmentConfig.monitoring_waypoints
    expect(updatedWaypoints.length).toBe(initialCount)
  })

  it('adds and removes geometric hazards', () => {
    const store = useMissionStore.getState()
    const initialObsCount = store.environmentConfig.obstacles.length

    const newObs = {
      id: 'OBS_NEW_TREE',
      type: 'circle' as const,
      x: 22,
      y: 33,
      z: 15,
      radius: 3.5,
    }
    store.addObstacle(newObs)

    let updatedObstacles = useMissionStore.getState().environmentConfig.obstacles
    expect(updatedObstacles.length).toBe(initialObsCount + 1)

    useMissionStore.getState().removeObstacle('OBS_NEW_TREE')
    updatedObstacles = useMissionStore.getState().environmentConfig.obstacles
    expect(updatedObstacles.length).toBe(initialObsCount)
  })

  it('executes demo route plan generation cleanly', async () => {
    const store = useMissionStore.getState()
    expect(store.isPlanning).toBe(false)

    await store.planRoute()

    const finalState = useMissionStore.getState()
    expect(finalState.isPlanning).toBe(false)
    expect(finalState.currentRoutePlan).not.toBeNull()
    expect(finalState.currentRoutePlan?.validation.is_valid).toBe(true)
  })
})
