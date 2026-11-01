import React from 'react'
import { Navigation, Compass, Gauge, Shield, Battery, Target } from 'lucide-react'
import { TelemetryPacket } from '../../types/telemetry'
import { Card } from '../common/Card'
import { Badge } from '../common/Badge'
import { formatDistance, formatSpeed, formatAltitude, formatPercentage } from '../../utils/formatters'

export interface TelemetryPanelProps {
  telemetry: TelemetryPacket
}

export const TelemetryPanel: React.FC<TelemetryPanelProps> = ({ telemetry }) => {
  const { position, velocity, target, flight_state, danger_level, battery_pct, uav_armed, api_control_enabled } =
    telemetry

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {/* Position 3D */}
      <Card className="p-3 bg-[#0b1322] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Position (ENU)</span>
          <Navigation className="w-3.5 h-3.5 text-sky-400" />
        </div>
        <div className="text-sm font-bold font-mono text-slate-100">
          [{position.x.toFixed(1)}, {position.y.toFixed(1)}]
        </div>
        <div className="text-[11px] font-mono text-cyan-400 mt-0.5">
          Alt: {formatAltitude(position.z)}
        </div>
      </Card>

      {/* Speed & Velocity Vector */}
      <Card className="p-3 bg-[#0b1322] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Air Speed</span>
          <Gauge className="w-3.5 h-3.5 text-emerald-400" />
        </div>
        <div className="text-sm font-bold font-mono text-emerald-400">
          {formatSpeed(velocity.speed)}
        </div>
        <div className="text-[10px] font-mono text-slate-500 mt-0.5">
          Vx: {velocity.vx} | Vy: {velocity.vy}
        </div>
      </Card>

      {/* Current Waypoint Target */}
      <Card className="p-3 bg-[#0b1322] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Target WP</span>
          <Target className="w-3.5 h-3.5 text-cyan-400" />
        </div>
        <div className="text-sm font-bold font-mono text-cyan-300">
          {target.waypoint_id}
        </div>
        <div className="text-[11px] font-mono text-slate-400 mt-0.5">
          Dist: {formatDistance(target.distance_to_target_m)}
        </div>
      </Card>

      {/* Flight State */}
      <Card className="p-3 bg-[#0b1322] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Flight State</span>
          <Compass className="w-3.5 h-3.5 text-purple-400" />
        </div>
        <div className="mt-1">
          <Badge variant="primary" className="text-[11px] font-mono py-0.5">
            {flight_state}
          </Badge>
        </div>
        <div className="text-[10px] font-mono text-slate-500 mt-1">
          {uav_armed ? 'ARMED' : 'DISARMED'} • {api_control_enabled ? 'API CTRL' : 'MANUAL'}
        </div>
      </Card>

      {/* Safety Layer Danger Level */}
      <Card className="p-3 bg-[#0b1322] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Safety Status</span>
          <Shield className="w-3.5 h-3.5 text-amber-400" />
        </div>
        <div className="mt-1">
          <Badge
            variant={danger_level === 'SAFE' ? 'safe' : danger_level === 'WARNING' ? 'warning' : 'danger'}
            className="text-[11px] font-mono py-0.5"
            pulse={danger_level !== 'SAFE'}
          >
            {danger_level}
          </Badge>
        </div>
        <div className="text-[10px] font-mono text-slate-500 mt-1">
          Obs: {formatDistance(telemetry.closest_obstacle_distance_m)}
        </div>
      </Card>

      {/* Battery State */}
      <Card className="p-3 bg-[#0b1322] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Battery State</span>
          <Battery className="w-3.5 h-3.5 text-sky-400" />
        </div>
        <div className="text-sm font-bold font-mono text-slate-100">
          {formatPercentage(battery_pct ?? 95)}
        </div>
        <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
          <div
            className={`h-full ${
              (battery_pct ?? 95) > 50
                ? 'bg-emerald-500'
                : (battery_pct ?? 95) > 20
                ? 'bg-amber-500'
                : 'bg-rose-500'
            }`}
            style={{ width: `${battery_pct ?? 95}%` }}
          />
        </div>
      </Card>
    </div>
  )
}
