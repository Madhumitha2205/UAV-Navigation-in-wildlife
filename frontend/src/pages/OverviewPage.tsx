import React from 'react'
import {
  Navigation,
  Gauge,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Layers,
  Activity,
  CheckCircle,
} from 'lucide-react'
import { useMissionStore } from '../store/missionStore'
import { useTelemetryStore } from '../store/telemetryStore'
import { useSettingsStore } from '../store/settingsStore'
import { useConnectionStatus } from '../hooks/useConnectionStatus'
import { MetricCard } from '../components/dashboard/MetricCard'
import { ActivityFeed } from '../components/dashboard/ActivityFeed'
import { EnvironmentMap } from '../components/planner/EnvironmentMap'
import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { formatAltitude, formatSpeed, formatPercentage } from '../utils/formatters'

export const OverviewPage: React.FC = () => {
  const { currentRoutePlan, recentActivities } = useMissionStore()
  const { telemetry } = useTelemetryStore()
  const { demoMode } = useSettingsStore()
  const connection = useConnectionStatus()

  return (
    <div className="space-y-6">
      {/* Top Header Mission Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-4 rounded-xl bg-[#0c1424] border border-slate-800">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-bold text-slate-100 tracking-wide">
              AUTONOMOUS MISSION CONTROL CENTER
            </h1>
            {demoMode ? (
              <Badge variant="demo" pulse>
                SIMULATED DEMO ACTIVE
              </Badge>
            ) : (
              <Badge variant="safe" pulse>
                LIVE TELEMETRY FEED
              </Badge>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Active Mission:{' '}
            <span className="text-sky-400 font-semibold">
              {currentRoutePlan?.mission_id || 'wildlife_monitoring_corridor_01'}
            </span>{' '}
            • Environment:{' '}
            <span className="text-slate-300">
              {currentRoutePlan?.coordinate_convention?.frame || 'ENU_ALT_UP'}
            </span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center gap-2">
            <span className="text-slate-500">AIRSIM:</span>
            <Badge
              variant={connection.airsim_simulation === 'CONNECTED' ? 'safe' : 'warning'}
              className="py-0 px-2 text-[10px]"
            >
              {connection.airsim_simulation}
            </Badge>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center gap-2">
            <span className="text-slate-500">FLIGHT STATE:</span>
            <span className="text-sky-300 font-bold">{telemetry.flight_state}</span>
          </div>
        </div>
      </div>

      {/* Summary Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        <MetricCard
          title="Total Runs"
          value="18"
          sublabel="Planned runs"
          icon={<Layers className="w-3.5 h-3.5" />}
        />
        <MetricCard
          title="Completed"
          value="16"
          sublabel="Zero collisions"
          variant="safe"
          icon={<CheckCircle className="w-3.5 h-3.5" />}
        />
        <MetricCard
          title="Mission State"
          value={telemetry.flight_state}
          sublabel="Current phase"
          variant="primary"
          icon={<Activity className="w-3.5 h-3.5" />}
        />
        <MetricCard
          title="UAV Altitude"
          value={formatAltitude(telemetry.position.z)}
          sublabel="Positive Up (m)"
          icon={<Navigation className="w-3.5 h-3.5" />}
        />
        <MetricCard
          title="UAV Speed"
          value={formatSpeed(telemetry.velocity.speed)}
          sublabel="Air velocity"
          variant="safe"
          icon={<Gauge className="w-3.5 h-3.5" />}
        />
        <MetricCard
          title="Monitoring"
          value={formatPercentage(currentRoutePlan?.path_metrics.monitoring_coverage_pct ?? 100)}
          sublabel="Target coverage"
          variant="safe"
          icon={<ShieldCheck className="w-3.5 h-3.5" />}
        />
        <MetricCard
          title="Collisions"
          value="0"
          sublabel="Safety barrier"
          variant="safe"
          icon={<AlertTriangle className="w-3.5 h-3.5" />}
        />
        <MetricCard
          title="Interventions"
          value={telemetry.safety_intervention ? '14' : '0'}
          sublabel="AFL safety kicks"
          variant="warning"
          icon={<ShieldAlert className="w-3.5 h-3.5" />}
        />
      </div>

      {/* Overview Visualization and Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Large 2D Environment Map View */}
        <div className="lg:col-span-2">
          <Card
            title="Real-Time Spatial Mission Map (ENU Coordinate Frame)"
            subtitle="Global route trajectory, static obstacles, monitoring targets, and live UAV telemetry"
            icon={<Navigation className="w-4 h-4 text-sky-400" />}
          >
            <EnvironmentMap
              routePlan={currentRoutePlan}
              uavPosition={telemetry.position}
              height={440}
            />
          </Card>
        </div>

        {/* Recent Activity Audit Feed */}
        <div className="lg:col-span-1">
          <ActivityFeed events={recentActivities} />
        </div>
      </div>
    </div>
  )
}
