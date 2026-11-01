import React from 'react'
import { CheckCircle2, AlertOctagon, Ruler, Clock, Layers, ShieldCheck } from 'lucide-react'
import { GlobalRoutePlan } from '../../types/route'
import { Card } from '../common/Card'
import { Badge } from '../common/Badge'
import { formatDistance, formatDuration, formatPercentage } from '../../utils/formatters'

export interface RouteMetricsProps {
  routePlan?: GlobalRoutePlan | null
}

export const RouteMetrics: React.FC<RouteMetricsProps> = ({ routePlan }) => {
  if (!routePlan) return null

  const { path_metrics, validation, monitoring_waypoints } = routePlan

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {/* Planned Length */}
      <Card className="p-3 bg-[#0c1424] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Path Length</span>
          <Ruler className="w-3.5 h-3.5 text-sky-400" />
        </div>
        <div className="text-lg font-bold text-slate-100 font-mono">
          {formatDistance(path_metrics.planned_path_length_m)}
        </div>
        <span className="text-[10px] text-slate-500">Global 3D euclidean</span>
      </Card>

      {/* Monitoring Waypoints */}
      <Card className="p-3 bg-[#0c1424] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Waypoints</span>
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
        </div>
        <div className="text-lg font-bold text-slate-100 font-mono">
          {path_metrics.num_monitoring_waypoints}
          <span className="text-xs text-slate-500 font-normal"> / {monitoring_waypoints.length}</span>
        </div>
        <span className="text-[10px] text-slate-500">Ordered sequence</span>
      </Card>

      {/* Coverage */}
      <Card className="p-3 bg-[#0c1424] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Coverage</span>
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
        </div>
        <div className="text-lg font-bold text-emerald-400 font-mono">
          {formatPercentage(path_metrics.monitoring_coverage_pct ?? 100)}
        </div>
        <span className="text-[10px] text-slate-500">Monitoring targets</span>
      </Card>

      {/* Clearance */}
      <Card className="p-3 bg-[#0c1424] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Min Clearance</span>
          <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
        </div>
        <div className="text-lg font-bold text-amber-400 font-mono">
          {formatDistance(path_metrics.minimum_obstacle_clearance_m ?? 3.1)}
        </div>
        <span className="text-[10px] text-slate-500">To nearest hazard</span>
      </Card>

      {/* Planning Time */}
      <Card className="p-3 bg-[#0c1424] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Solve Time</span>
          <Clock className="w-3.5 h-3.5 text-purple-400" />
        </div>
        <div className="text-lg font-bold text-slate-100 font-mono">
          {formatDuration(validation.planning_time_sec)}
        </div>
        <span className="text-[10px] text-slate-500">GA + 2-Opt runtime</span>
      </Card>

      {/* Validation Status */}
      <Card className="p-3 bg-[#0c1424] border-slate-800">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-[11px] font-mono uppercase">Status</span>
          {validation.is_valid ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <AlertOctagon className="w-3.5 h-3.5 text-rose-400" />
          )}
        </div>
        <div className="mt-1">
          <Badge
            variant={validation.is_valid ? 'safe' : 'danger'}
            className="text-[11px] font-mono py-0.5"
          >
            {validation.status}
          </Badge>
        </div>
        <span className="text-[10px] text-slate-500 mt-1 block">
          {validation.collision_free ? 'Collision-free' : 'Hazard collision'}
        </span>
      </Card>
    </div>
  )
}
