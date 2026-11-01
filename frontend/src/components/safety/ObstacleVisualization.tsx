import React from 'react'
import { Card } from '../common/Card'
import { TelemetryPacket } from '../../types/telemetry'
import { Radio } from 'lucide-react'

export interface ObstacleVisualizationProps {
  telemetry: TelemetryPacket
}

export const ObstacleVisualization: React.FC<ObstacleVisualizationProps> = ({ telemetry }) => {
  const { closest_obstacle_distance_m, closest_obstacle_id, danger_level } = telemetry

  // Scale: 12 meters = radius of radar (140px)
  const maxRangeM = 12.0
  const radarRadius = 130
  const center = 150

  const getRadiusForDist = (d: number) => (Math.min(d, maxRangeM) / maxRangeM) * radarRadius

  // Compute mock bearing position for closest obstacle
  const obsDist = Math.max(0.5, closest_obstacle_distance_m)
  const angleRad = -Math.PI / 4 // 45 deg forward right
  const obsR = getRadiusForDist(obsDist)
  const obsX = center + obsR * Math.cos(angleRad)
  const obsY = center + obsR * Math.sin(angleRad)

  return (
    <Card
      title="Proximity Radar & Dynamic Safety Envelopes"
      subtitle="Multi-zone distance thresholds: Critical (<2.5m), Warning (2.5-6.0m), Safe (>6.0m)"
      icon={<Radio className="w-4 h-4 text-emerald-400" />}
    >
      <div className="flex flex-col md:flex-row items-center justify-around gap-6">
        {/* Radar View */}
        <div className="relative w-[300px] h-[300px] bg-slate-950/80 rounded-full border border-slate-800 shadow-inner flex items-center justify-center overflow-hidden">
          <svg width="300" height="300" className="absolute inset-0">
            {/* Safe Zone (Outer Ring) */}
            <circle
              cx={center}
              cy={center}
              r={radarRadius}
              fill="rgba(16, 185, 129, 0.04)"
              stroke="#10b981"
              strokeWidth="1"
              strokeDasharray="4 4"
            />
            {/* Warning Zone (6.0m threshold) */}
            <circle
              cx={center}
              cy={center}
              r={getRadiusForDist(6.0)}
              fill="rgba(245, 158, 11, 0.06)"
              stroke="#f59e0b"
              strokeWidth="1.5"
              strokeDasharray="3 3"
            />
            {/* Critical Zone (2.5m threshold) */}
            <circle
              cx={center}
              cy={center}
              r={getRadiusForDist(2.5)}
              fill="rgba(239, 68, 68, 0.12)"
              stroke="#ef4444"
              strokeWidth="1.5"
            />
            {/* Collision Radius (1.0m threshold) */}
            <circle
              cx={center}
              cy={center}
              r={getRadiusForDist(1.0)}
              fill="rgba(239, 68, 68, 0.3)"
              stroke="#ef4444"
              strokeWidth="2"
            />

            {/* Radar Crosshairs */}
            <line x1={center} y1="10" x2={center} y2="290" stroke="#1e293b" strokeWidth="1" />
            <line x1="10" y1={center} x2="290" y2={center} stroke="#1e293b" strokeWidth="1" />

            {/* Closest Obstacle Blip */}
            <g>
              <circle
                cx={obsX}
                cy={obsY}
                r="6"
                fill={danger_level === 'CRITICAL' ? '#ef4444' : danger_level === 'WARNING' ? '#f59e0b' : '#38bdf8'}
                stroke="#ffffff"
                strokeWidth="1.5"
                className="animate-pulse"
              />
              <line
                x1={center}
                y1={center}
                x2={obsX}
                y2={obsY}
                stroke={danger_level === 'CRITICAL' ? '#ef4444' : '#f59e0b'}
                strokeWidth="1"
                strokeDasharray="2 2"
              />
              <text
                x={obsX + 8}
                y={obsY - 4}
                fill="#f8fafc"
                fontSize="10"
                className="font-mono font-bold"
              >
                {closest_obstacle_id} ({obsDist.toFixed(1)}m)
              </text>
            </g>

            {/* Center Drone */}
            <circle cx={center} cy={center} r="5" fill="#0ea5e9" stroke="#ffffff" strokeWidth="2" />
            <text x={center} y={center + 16} fill="#38bdf8" fontSize="10" textAnchor="middle" className="font-mono font-bold">
              UAV
            </text>
          </svg>
        </div>

        {/* Legend & Thresholds Breakdown */}
        <div className="space-y-3 max-w-sm text-xs font-mono">
          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800 space-y-2">
            <span className="text-[11px] font-bold text-slate-300 uppercase block border-b border-slate-800 pb-1">
              Active Fuzzy Safety Thresholds
            </span>
            <div className="flex justify-between items-center text-emerald-400">
              <span>Safe Buffer Zone:</span>
              <span>&gt; 6.0 m</span>
            </div>
            <div className="flex justify-between items-center text-amber-400">
              <span>Warning Damping Zone:</span>
              <span>2.5 m - 6.0 m</span>
            </div>
            <div className="flex justify-between items-center text-rose-400">
              <span>Critical Emergency Brake:</span>
              <span>&lt; 2.5 m</span>
            </div>
            <div className="flex justify-between items-center text-rose-500 font-bold">
              <span>Physical Collision Radius:</span>
              <span>1.0 m</span>
            </div>
          </div>
          <p className="text-[11px] text-slate-400 font-sans leading-relaxed">
            Real-time proximity vectors evaluated by the Adaptive Fuzzy Logic (AFL) controller.
            When obstacles breach the 6.0m margin, fuzzy repulsive forces continuously redirect the UAV.
          </p>
        </div>
      </div>
    </Card>
  )
}
