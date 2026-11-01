import React from 'react'
import { Shield, ShieldAlert, AlertTriangle, Compass, CheckCircle } from 'lucide-react'
import { TelemetryPacket, DangerLevel } from '../../types/telemetry'
import { Card } from '../common/Card'
import { Badge } from '../common/Badge'
import { formatDistance } from '../../utils/formatters'

export interface SafetyStatusProps {
  telemetry: TelemetryPacket
}

export const SafetyStatus: React.FC<SafetyStatusProps> = ({ telemetry }) => {
  const { danger_level, closest_obstacle_distance_m, closest_obstacle_id, safety_intervention } =
    telemetry

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
      {/* Current Danger Classification */}
      <Card className="p-3 bg-[#0c1424] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Danger Level</span>
          <ShieldAlert className="w-4 h-4 text-amber-400" />
        </div>
        <div className="mt-1">
          <Badge
            variant={danger_level === 'SAFE' ? 'safe' : danger_level === 'WARNING' ? 'warning' : 'danger'}
            className="text-xs font-mono font-bold py-1 px-3"
            pulse={danger_level !== 'SAFE'}
          >
            {danger_level}
          </Badge>
        </div>
        <span className="text-[10px] text-slate-500 mt-1 block">
          AFL membership fuzzy state
        </span>
      </Card>

      {/* Closest Hazard Distance */}
      <Card className="p-3 bg-[#0c1424] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Closest Hazard</span>
          <AlertTriangle className="w-4 h-4 text-rose-400" />
        </div>
        <div className="text-xl font-bold font-mono text-slate-100">
          {formatDistance(closest_obstacle_distance_m)}
        </div>
        <span className="text-[10px] text-slate-500 mt-1 block">
          ID: {closest_obstacle_id || 'NONE'}
        </span>
      </Card>

      {/* Adaptive Fuzzy Intervention */}
      <Card className="p-3 bg-[#0c1424] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">AFL Intervention</span>
          <Shield className="w-4 h-4 text-sky-400" />
        </div>
        <div className="mt-1">
          <Badge
            variant={safety_intervention ? 'warning' : 'safe'}
            className="text-xs font-mono py-1 px-2.5"
          >
            {safety_intervention ? 'ACTIVE CORRECTION' : 'INACTIVE (NOMINAL)'}
          </Badge>
        </div>
        <span className="text-[10px] text-slate-500 mt-1 block">
          Fuzzy repulsive vector active
        </span>
      </Card>

      {/* Sensor Array Status */}
      <Card className="p-3 bg-[#0c1424] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Sensors & Lidar</span>
          <CheckCircle className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="text-sm font-semibold font-mono text-emerald-400 mt-0.5">
          HEALTHY (360° LiDAR)
        </div>
        <span className="text-[10px] text-slate-500 mt-1 block">
          AirSim distance sensor active
        </span>
      </Card>
    </div>
  )
}
