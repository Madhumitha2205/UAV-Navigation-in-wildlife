import { Point3D } from '../types/environment'

/**
 * Coordinate Transformations based on INTEGRATION_GUIDE.md:
 * Global Planner Frame (ENU_ALT_UP):
 *   X = East (m)
 *   Y = North (m)
 *   Z = Altitude Up (m)
 * 
 * AirSim Multirotor Frame (NED):
 *   North = +Y_planner
 *   East  = +X_planner
 *   Down  = -Z_planner
 */

export interface AirSimNEDPoint {
  north: number
  east: number
  down: number
}

export function plannerToAirSim(point: Point3D): AirSimNEDPoint {
  return {
    north: point.y,
    east: point.x,
    down: -point.z,
  }
}

export function airSimToPlanner(ned: AirSimNEDPoint): Point3D {
  return {
    x: ned.east,
    y: ned.north,
    z: -ned.down,
  }
}

export interface Bounds2D {
  minX: number
  maxX: number
  minY: number
  maxY: number
  width: number
  height: number
}

export function computeBounds(
  points: { x: number; y: number }[],
  paddingRatio = 0.15,
  minWidth = 50,
  minHeight = 50
): Bounds2D {
  if (points.length === 0) {
    return { minX: 0, maxX: 100, minY: 0, maxY: 100, width: 100, height: 100 }
  }

  let minX = Math.min(...points.map((p) => p.x))
  let maxX = Math.max(...points.map((p) => p.x))
  let minY = Math.min(...points.map((p) => p.y))
  let maxY = Math.max(...points.map((p) => p.y))

  const width = Math.max(maxX - minX, minWidth)
  const height = Math.max(maxY - minY, minHeight)

  const padX = width * paddingRatio
  const padY = height * paddingRatio

  return {
    minX: minX - padX,
    maxX: maxX + padX,
    minY: minY - padY,
    maxY: maxY + padY,
    width: width + padX * 2,
    height: height + padY * 2,
  }
}

/**
 * Projects a 2D planner coordinate (X East, Y North) to Canvas/SVG coordinates.
 * Note: In Canvas/SVG, Y=0 is at the TOP, so we invert Y so positive Y is rendered upwards.
 */
export function projectToCanvas(
  x: number,
  y: number,
  bounds: Bounds2D,
  viewWidth: number,
  viewHeight: number
): { cx: number; cy: number } {
  const normX = (x - bounds.minX) / (bounds.width || 1)
  const normY = (y - bounds.minY) / (bounds.height || 1)

  const cx = normX * viewWidth
  const cy = (1 - normY) * viewHeight // Invert Y for standard Cartesian display

  return { cx, cy }
}

export function canvasToPlanner(
  cx: number,
  cy: number,
  bounds: Bounds2D,
  viewWidth: number,
  viewHeight: number
): { x: number; y: number } {
  const normX = cx / viewWidth
  const normY = 1 - cy / viewHeight

  const x = bounds.minX + normX * bounds.width
  const y = bounds.minY + normY * bounds.height

  return { x: Number(x.toFixed(2)), y: Number(y.toFixed(2)) }
}
