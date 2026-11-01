import React, { useState, useRef, useMemo, useEffect } from 'react'
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Eye,
  EyeOff,
  Crosshair,
  Shield,
  Layers,
  MapPin,
  CircleDot,
  Info,
} from 'lucide-react'
import { GlobalRoutePlan } from '../../types/route'
import { StaticObstacle, MonitoringWaypoint, Point3D } from '../../types/environment'
import { computeBounds, projectToCanvas, canvasToPlanner, Bounds2D } from '../../utils/coordinateUtils'
import { Button } from '../common/Button'
import { Badge } from '../common/Badge'

export interface EnvironmentMapProps {
  routePlan?: GlobalRoutePlan | null
  uavPosition?: Point3D | null
  width?: number | string
  height?: number | string
  allowMapClickToAdd?: boolean
  onAddPoint?: (point: { x: number; y: number }) => void
  onSelectWaypoint?: (wp: MonitoringWaypoint | null) => void
  onSelectObstacle?: (obs: StaticObstacle | null) => void
  selectedWaypointId?: string | null
  selectedObstacleId?: string | null
}

export const EnvironmentMap: React.FC<EnvironmentMapProps> = ({
  routePlan,
  uavPosition,
  height = 540,
  allowMapClickToAdd = false,
  onAddPoint,
  onSelectWaypoint,
  onSelectObstacle,
  selectedWaypointId,
  selectedObstacleId,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [zoom, setZoom] = useState<number>(1)
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 })
  const [selectedInspect, setSelectedInspect] = useState<string | null>(null)

  // Layer toggles
  const [showObstacles, setShowObstacles] = useState(true)
  const [showSafetyBuffer, setShowSafetyBuffer] = useState(true)
  const [showOptimizedRoute, setShowOptimizedRoute] = useState(true)
  const [showInitialRoute, setShowInitialRoute] = useState(false)
  const [showIntermediatePoints, setShowIntermediatePoints] = useState(true)
  const [showWaypointLabels, setShowWaypointLabels] = useState(true)

  // Viewport dimensions
  const [dims, setDims] = useState<{ width: number; height: number }>({ width: 700, height: 480 })

  useEffect(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect()
      setDims({
        width: Math.max(rect.width, 300),
        height: typeof height === 'number' ? height : 480,
      })
    }
  }, [height])

  // Collect all spatial coordinates for bounding box
  const allPoints = useMemo(() => {
    const pts: { x: number; y: number }[] = []
    if (!routePlan) return pts

    pts.push(routePlan.start_position)
    pts.push(routePlan.destination)
    routePlan.monitoring_waypoints.forEach((wp) => pts.push(wp))
    routePlan.intermediate_path_points.forEach((pt) => pts.push(pt))
    routePlan.static_obstacles.forEach((obs) => {
      if (obs.type === 'circle') {
        pts.push({ x: obs.x - obs.radius, y: obs.y - obs.radius })
        pts.push({ x: obs.x + obs.radius, y: obs.y + obs.radius })
      } else {
        pts.push({ x: obs.min_x, y: obs.min_y })
        pts.push({ x: obs.max_x, y: obs.max_y })
      }
    })
    if (uavPosition) {
      pts.push(uavPosition)
    }
    return pts
  }, [routePlan, uavPosition])

  const bounds: Bounds2D = useMemo(() => {
    return computeBounds(allPoints, 0.15, 60, 50)
  }, [allPoints])

  // Reset viewport fit
  const handleFitRoute = () => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }

  // Pan interaction
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return
    setIsDragging(true)
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    })
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  // Zoom wheel
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85
    setZoom((z) => Math.min(Math.max(z * zoomFactor, 0.5), 5.0))
  }

  // Click on canvas to add point or inspect
  const handleCanvasClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const clickX = (e.clientX - rect.left - pan.x) / zoom
    const clickY = (e.clientY - rect.top - pan.y) / zoom

    if (allowMapClickToAdd && onAddPoint) {
      const coord = canvasToPlanner(clickX, clickY, bounds, dims.width, dims.height)
      onAddPoint(coord)
    }
  }

  // Pre-project optimized route polyline points
  const optimizedPointsString = useMemo(() => {
    if (!routePlan || !showOptimizedRoute) return ''
    return routePlan.intermediate_path_points
      .map((pt) => {
        const { cx, cy } = projectToCanvas(pt.x, pt.y, bounds, dims.width, dims.height)
        return `${cx},${cy}`
      })
      .join(' ')
  }, [routePlan, bounds, dims, showOptimizedRoute])

  // Pre-project initial unoptimized route polyline
  const initialPointsString = useMemo(() => {
    if (!routePlan?.initial_unoptimized_path_points || !showInitialRoute) return ''
    return routePlan.initial_unoptimized_path_points
      .map((pt) => {
        const { cx, cy } = projectToCanvas(pt.x, pt.y, bounds, dims.width, dims.height)
        return `${cx},${cy}`
      })
      .join(' ')
  }, [routePlan, bounds, dims, showInitialRoute])

  return (
    <div
      ref={containerRef}
      className="relative rounded-xl border border-slate-800 bg-[#070b14] overflow-hidden select-none"
      style={{ height }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
    >
      {/* Map Control Toolbar */}
      <div className="absolute top-3 right-3 z-20 flex items-center gap-1.5 bg-slate-900/90 border border-slate-800 rounded-lg p-1.5 shadow-lg backdrop-blur-md">
        <Button
          variant="ghost"
          size="sm"
          className="p-1.5 h-7 w-7 text-slate-300 hover:text-white"
          onClick={() => setZoom((z) => Math.min(z * 1.25, 5))}
          title="Zoom In"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="p-1.5 h-7 w-7 text-slate-300 hover:text-white"
          onClick={() => setZoom((z) => Math.max(z * 0.8, 0.5))}
          title="Zoom Out"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="p-1.5 h-7 w-7 text-slate-300 hover:text-white"
          onClick={handleFitRoute}
          title="Fit Route to Viewport"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </Button>
        <div className="w-[1px] h-4 bg-slate-800 mx-1" />
        <Button
          variant={showObstacles ? 'primary' : 'outline'}
          size="sm"
          className="px-2 h-7 text-[10px]"
          onClick={() => setShowObstacles(!showObstacles)}
          title="Toggle Obstacles"
        >
          Obstacles
        </Button>
        <Button
          variant={showSafetyBuffer ? 'primary' : 'outline'}
          size="sm"
          className="px-2 h-7 text-[10px]"
          onClick={() => setShowSafetyBuffer(!showSafetyBuffer)}
          title="Toggle Safety Clearance Buffer"
        >
          Safety
        </Button>
        <Button
          variant={showInitialRoute ? 'primary' : 'outline'}
          size="sm"
          className="px-2 h-7 text-[10px]"
          onClick={() => setShowInitialRoute(!showInitialRoute)}
          title="Toggle Initial Unoptimized Route"
        >
          Initial Path
        </Button>
      </div>

      {/* Coordinate & Frame Badge */}
      <div className="absolute bottom-3 left-3 z-20 flex items-center gap-2 bg-slate-950/85 border border-slate-800/80 rounded-md px-3 py-1.5 text-[11px] font-mono text-slate-400 backdrop-blur-sm">
        <span className="text-sky-400 font-semibold">FRAME:</span> ENU_ALT_UP (X:East, Y:North)
        <span className="text-slate-600">|</span>
        <span className="text-slate-400">ZOOM: {Math.round(zoom * 100)}%</span>
      </div>

      {/* Selected Element Inspection Floating Panel */}
      {selectedInspect && (
        <div className="absolute top-3 left-3 z-20 bg-slate-900/95 border border-sky-500/40 rounded-lg p-3 max-w-xs shadow-xl text-xs backdrop-blur-md">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
            <span className="font-mono text-sky-300 font-semibold">{selectedInspect}</span>
            <button
              onClick={() => setSelectedInspect(null)}
              className="text-slate-400 hover:text-white"
            >
              ×
            </button>
          </div>
          <p className="text-slate-300 mt-2 text-[11px]">
            Selected waypoint / obstacle details inspected from simulation map coordinate frame.
          </p>
        </div>
      )}

      {/* Main SVG Render Canvas */}
      <svg
        className="w-full h-full cursor-grab active:cursor-grabbing"
        onClick={handleCanvasClick}
      >
        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {/* Background Grid Pattern */}
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#121b2f" strokeWidth="1" />
            </pattern>
            {/* Start Gradient */}
            <linearGradient id="startGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="100%" stopColor="#047857" />
            </linearGradient>
            {/* Dest Gradient */}
            <linearGradient id="destGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#f43f5e" />
              <stop offset="100%" stopColor="#be123c" />
            </linearGradient>
            {/* Route Glow Filter */}
            <filter id="routeGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Grid Fill */}
          <rect
            x={-dims.width * 2}
            y={-dims.height * 2}
            width={dims.width * 5}
            height={dims.height * 5}
            fill="url(#grid)"
          />

          {/* Safety Buffers and Clearance Circles */}
          {showSafetyBuffer &&
            showObstacles &&
            routePlan?.static_obstacles.map((obs) => {
              if (obs.type === 'circle') {
                const { cx, cy } = projectToCanvas(obs.x, obs.y, bounds, dims.width, dims.height)
                const scaleX = dims.width / bounds.width
                const safetyR = (obs.radius + 3.0) * scaleX
                return (
                  <circle
                    key={`buffer-${obs.id}`}
                    cx={cx}
                    cy={cy}
                    r={safetyR}
                    fill="rgba(245, 158, 11, 0.08)"
                    stroke="rgba(245, 158, 11, 0.25)"
                    strokeWidth="1.5"
                    strokeDasharray="4 4"
                  />
                )
              }
              return null
            })}

          {/* Static Obstacles */}
          {showObstacles &&
            routePlan?.static_obstacles.map((obs) => {
              const isSelected = selectedObstacleId === obs.id
              if (obs.type === 'circle') {
                const { cx, cy } = projectToCanvas(obs.x, obs.y, bounds, dims.width, dims.height)
                const scaleX = dims.width / bounds.width
                const r = obs.radius * scaleX

                return (
                  <g
                    key={obs.id}
                    className="cursor-pointer group"
                    onClick={(e) => {
                      e.stopPropagation()
                      onSelectObstacle?.(obs)
                      setSelectedInspect(`Obstacle: ${obs.id} (R=${obs.radius}m)`)
                    }}
                  >
                    <circle
                      cx={cx}
                      cy={cy}
                      r={r}
                      fill={isSelected ? '#7f1d1d' : '#33111b'}
                      stroke={isSelected ? '#f43f5e' : '#e11d48'}
                      strokeWidth={isSelected ? '2.5' : '1.5'}
                      className="transition-all hover:fill-rose-900/60"
                    />
                    <text
                      x={cx}
                      y={cy + 3}
                      fill="#fda4af"
                      fontSize="9"
                      textAnchor="middle"
                      className="font-mono font-medium pointer-events-none"
                    >
                      {obs.id.replace('OBS_', '')}
                    </text>
                  </g>
                )
              } else {
                // Rectangular obstacle
                const pMin = projectToCanvas(obs.min_x, obs.max_y, bounds, dims.width, dims.height)
                const pMax = projectToCanvas(obs.max_x, obs.min_y, bounds, dims.width, dims.height)
                const rectW = Math.abs(pMax.cx - pMin.cx)
                const rectH = Math.abs(pMax.cy - pMin.cy)

                return (
                  <g
                    key={obs.id}
                    className="cursor-pointer"
                    onClick={(e) => {
                      e.stopPropagation()
                      onSelectObstacle?.(obs)
                      setSelectedInspect(`Obstacle: ${obs.id} [${obs.min_x},${obs.min_y}]-[${obs.max_x},${obs.max_y}]`)
                    }}
                  >
                    <rect
                      x={pMin.cx}
                      y={pMin.cy}
                      width={rectW}
                      height={rectH}
                      fill={isSelected ? '#7f1d1d' : '#2d141e'}
                      stroke={isSelected ? '#f43f5e' : '#be123c'}
                      strokeWidth={isSelected ? '2.5' : '1.5'}
                      rx="3"
                    />
                    <text
                      x={pMin.cx + rectW / 2}
                      y={pMin.cy + rectH / 2 + 3}
                      fill="#fda4af"
                      fontSize="9"
                      textAnchor="middle"
                      className="font-mono font-medium pointer-events-none"
                    >
                      {obs.id.replace('OBS_', '')}
                    </text>
                  </g>
                )
              }
            })}

          {/* Initial Unoptimized Route (comparison) */}
          {showInitialRoute && initialPointsString && (
            <polyline
              points={initialPointsString}
              fill="none"
              stroke="#64748b"
              strokeWidth="2"
              strokeDasharray="6 4"
              opacity="0.7"
            />
          )}

          {/* Optimized Global Route Polyline */}
          {showOptimizedRoute && optimizedPointsString && (
            <polyline
              points={optimizedPointsString}
              fill="none"
              stroke="#0ea5e9"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              filter="url(#routeGlow)"
            />
          )}

          {/* Intermediate A* Path Points */}
          {showIntermediatePoints &&
            routePlan?.intermediate_path_points.map((pt, idx) => {
              if (pt.waypoint_id === 'START' || pt.waypoint_id === 'DEST') return null
              const { cx, cy } = projectToCanvas(pt.x, pt.y, bounds, dims.width, dims.height)

              if (pt.is_monitoring) return null // Rendered separately as monitoring waypoint

              return (
                <circle
                  key={`pt-${idx}`}
                  cx={cx}
                  cy={cy}
                  r="3"
                  fill="#0369a1"
                  stroke="#38bdf8"
                  strokeWidth="1"
                />
              )
            })}

          {/* Monitoring Waypoints */}
          {routePlan?.monitoring_waypoints.map((wp) => {
            const { cx, cy } = projectToCanvas(wp.x, wp.y, bounds, dims.width, dims.height)
            const isSelected = selectedWaypointId === wp.id

            return (
              <g
                key={wp.id}
                className="cursor-pointer group"
                onClick={(e) => {
                  e.stopPropagation()
                  onSelectWaypoint?.(wp)
                  setSelectedInspect(`Waypoint: ${wp.id} (${wp.zone_name}) Priority: ${wp.priority}`)
                }}
              >
                {/* Priority Pulse Rings */}
                <circle
                  cx={cx}
                  cy={cy}
                  r={isSelected ? '16' : '12'}
                  fill="none"
                  stroke="#06b6d4"
                  strokeWidth="1.5"
                  strokeDasharray="2 2"
                  className="animate-pulse"
                />
                <circle
                  cx={cx}
                  cy={cy}
                  r="7"
                  fill={isSelected ? '#06b6d4' : '#0891b2'}
                  stroke="#ffffff"
                  strokeWidth="2"
                />
                {showWaypointLabels && (
                  <text
                    x={cx}
                    y={cy - 12}
                    fill="#a5f3fc"
                    fontSize="11"
                    fontWeight="bold"
                    textAnchor="middle"
                    className="font-mono drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]"
                  >
                    {wp.id}
                  </text>
                )}
              </g>
            )
          })}

          {/* Start Position Marker */}
          {routePlan?.start_position && (
            <g
              transform={`translate(${
                projectToCanvas(routePlan.start_position.x, routePlan.start_position.y, bounds, dims.width, dims.height).cx
              }, ${
                projectToCanvas(routePlan.start_position.x, routePlan.start_position.y, bounds, dims.width, dims.height).cy
              })`}
            >
              <circle r="9" fill="url(#startGrad)" stroke="#ffffff" strokeWidth="2" />
              <text y="3" fill="#ffffff" fontSize="9" fontWeight="bold" textAnchor="middle">
                S
              </text>
              <text y="20" fill="#34d399" fontSize="10" fontWeight="bold" textAnchor="middle" className="font-mono">
                START
              </text>
            </g>
          )}

          {/* Destination Marker */}
          {routePlan?.destination && (
            <g
              transform={`translate(${
                projectToCanvas(routePlan.destination.x, routePlan.destination.y, bounds, dims.width, dims.height).cx
              }, ${
                projectToCanvas(routePlan.destination.x, routePlan.destination.y, bounds, dims.width, dims.height).cy
              })`}
            >
              <circle r="9" fill="url(#destGrad)" stroke="#ffffff" strokeWidth="2" />
              <text y="3" fill="#ffffff" fontSize="9" fontWeight="bold" textAnchor="middle">
                D
              </text>
              <text y="20" fill="#f87171" fontSize="10" fontWeight="bold" textAnchor="middle" className="font-mono">
                DEST
              </text>
            </g>
          )}

          {/* Live UAV Position Marker */}
          {uavPosition && (
            <g
              transform={`translate(${
                projectToCanvas(uavPosition.x, uavPosition.y, bounds, dims.width, dims.height).cx
              }, ${
                projectToCanvas(uavPosition.x, uavPosition.y, bounds, dims.width, dims.height).cy
              })`}
            >
              {/* Radar pulse around drone */}
              <circle r="22" fill="rgba(14, 165, 233, 0.2)" stroke="#0ea5e9" strokeWidth="1" className="animate-ping" />
              <circle r="8" fill="#38bdf8" stroke="#ffffff" strokeWidth="2" />
              {/* Drone crosshair */}
              <line x1="-12" y1="0" x2="12" y2="0" stroke="#38bdf8" strokeWidth="1.5" />
              <line x1="0" y1="-12" x2="0" y2="12" stroke="#38bdf8" strokeWidth="1.5" />
              <text y="-14" fill="#38bdf8" fontSize="10" fontWeight="bold" textAnchor="middle" className="font-mono">
                UAV
              </text>
            </g>
          )}
        </g>
      </svg>
    </div>
  )
}
