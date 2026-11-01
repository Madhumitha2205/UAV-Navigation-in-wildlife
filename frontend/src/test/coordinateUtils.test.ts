import { describe, it, expect } from 'vitest'
import {
  plannerToAirSim,
  airSimToPlanner,
  computeBounds,
  projectToCanvas,
  canvasToPlanner,
} from '../utils/coordinateUtils'

describe('Coordinate Transformation and Canvas Projections', () => {
  it('correctly transforms planner coordinates (ENU_ALT_UP) to AirSim multirotor frame (NED)', () => {
    // ENU: East=20, North=15, AltUp=16
    const plannerPoint = { x: 20.0, y: 15.0, z: 16.0 }
    const airsim = plannerToAirSim(plannerPoint)

    // AirSim: North=+Y, East=+X, Down=-Z
    expect(airsim.north).toBe(15.0)
    expect(airsim.east).toBe(20.0)
    expect(airsim.down).toBe(-16.0)
  })

  it('correctly reverses AirSim NED coordinates back to planner frame', () => {
    const airsim = { north: 35.0, east: 45.0, down: -18.0 }
    const planner = airSimToPlanner(airsim)

    expect(planner.x).toBe(45.0)
    expect(planner.y).toBe(35.0)
    expect(planner.z).toBe(18.0)
  })

  it('computes 2D bounding boxes with safety margins', () => {
    const points = [
      { x: 0, y: 0 },
      { x: 100, y: 50 },
    ]
    const bounds = computeBounds(points, 0.1)

    expect(bounds.minX).toBeLessThan(0)
    expect(bounds.maxX).toBeGreaterThan(100)
    expect(bounds.minY).toBeLessThan(0)
    expect(bounds.maxY).toBeGreaterThan(50)
  })

  it('projects and unprojects points faithfully between planner and canvas space', () => {
    const bounds = { minX: 0, maxX: 100, minY: 0, maxY: 100, width: 100, height: 100 }
    const viewWidth = 500
    const viewHeight = 500

    // Test center point (50, 50)
    const { cx, cy } = projectToCanvas(50, 50, bounds, viewWidth, viewHeight)
    expect(cx).toBeCloseTo(250)
    expect(cy).toBeCloseTo(250) // Inverted Y: 1 - 0.5 = 0.5 -> 250

    const reconstructed = canvasToPlanner(cx, cy, bounds, viewWidth, viewHeight)
    expect(reconstructed.x).toBeCloseTo(50)
    expect(reconstructed.y).toBeCloseTo(50)
  })
})
