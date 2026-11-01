import React from 'react'
import { BarChart3, TrendingUp, CheckCircle, ShieldAlert, Zap, Clock, Ruler } from 'lucide-react'
import { PerformanceChart } from '../components/analytics/PerformanceChart'
import { Card } from '../components/common/Card'
import { MetricCard } from '../components/dashboard/MetricCard'
import { Badge } from '../components/common/Badge'
import { MOCK_ANALYTICS_SUMMARY } from '../mock/mockAnalytics'
import { formatDistance, formatDuration, formatPercentage } from '../utils/formatters'

export const MissionAnalyticsPage: React.FC = () => {
  const summary = MOCK_ANALYTICS_SUMMARY

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-[#0c1424] border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-slate-100 tracking-wide flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-sky-400" />
              POST-FLIGHT MISSION ANALYTICS
            </h1>
            <Badge variant="demo">EXPERIMENT EVALUATION</Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Quantitative assessment of completed mission trajectories, path deviations, safety barriers, and control effort
          </p>
        </div>

        <div className="text-xs font-mono text-slate-400">
          <span>MISSION ID:</span>{' '}
          <span className="text-sky-300 font-bold">{summary.mission_id}</span>
        </div>
      </div>

      {/* Analytics Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <MetricCard
          title="Completion"
          value={formatPercentage(summary.completion_rate_pct)}
          sublabel="Survey targets"
          variant="safe"
          icon={<CheckCircle className="w-3.5 h-3.5" />}
        />
        <MetricCard
          title="Planned Length"
          value={formatDistance(summary.planned_route_length_m)}
          sublabel="GA theoretical"
          icon={<Ruler className="w-3.5 h-3.5" />}
        />
        <MetricCard
          title="Actual Travelled"
          value={formatDistance(summary.actual_travelled_distance_m)}
          sublabel="+5.4% obstacle avoidance"
          variant="primary"
          icon={<TrendingUp className="w-3.5 h-3.5" />}
        />
        <MetricCard
          title="Collisions"
          value={summary.collision_count}
          sublabel="Zero collisions"
          variant="safe"
          icon={<CheckCircle className="w-3.5 h-3.5" />}
        />
        <MetricCard
          title="Min Clearance"
          value={formatDistance(summary.min_obstacle_distance_m)}
          sublabel="Closest hazard margin"
          variant="warning"
          icon={<ShieldAlert className="w-3.5 h-3.5" />}
        />
        <MetricCard
          title="Flight Duration"
          value={formatDuration(summary.execution_duration_sec)}
          sublabel="AirSim execution"
          icon={<Clock className="w-3.5 h-3.5" />}
        />
        <MetricCard
          title="Energy Proxy"
          value={`${summary.estimated_energy_proxy_joules} J`}
          sublabel="Kinematic effort proxy*"
          variant="safe"
          icon={<Zap className="w-3.5 h-3.5" />}
        />
      </div>

      {/* Performance Charts */}
      <PerformanceChart summary={summary} />

      {/* Academic Methodology Callout */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 space-y-1">
        <span className="font-mono text-slate-300 font-bold block">
          * Research Methodology & Kinematic Energy Proxy Note:
        </span>
        <p className="leading-relaxed">
          The reported energy proxy is computed using the kinematic control-effort integral (integral of ||a(t)||^2 dt) rather than direct hardware electrochemical dissipation.
          This directly quantifies controller smoothness and jerk reduction provided by the Adaptive Fuzzy Logic safety layer during dynamic obstacle encounters.
        </p>
      </div>
    </div>
  )
}
