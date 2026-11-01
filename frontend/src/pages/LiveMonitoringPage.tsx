import React from 'react'
import { Navigation, Radio, CheckCircle, Clock } from 'lucide-react'
import { useTelemetryStore } from '../store/telemetryStore'
import { useMissionStore } from '../store/missionStore'
import { useSettingsStore } from '../store/settingsStore'
import { TelemetryPanel } from '../components/monitoring/TelemetryPanel'
import { SimulationViewport } from '../components/monitoring/SimulationViewport'
import { SimulationControls } from '../components/monitoring/SimulationControls'
import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Badge'

export const LiveMonitoringPage: React.FC = () => {
  const { telemetry, connectionStatus } = useTelemetryStore()
  const { currentRoutePlan } = useMissionStore()
  const { demoMode } = useSettingsStore()

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-[#0c1424] border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-slate-100 tracking-wide flex items-center gap-2">
              <Navigation className="w-5 h-5 text-sky-400" />
              LIVE UAV SIMULATION MONITORING
            </h1>
            {demoMode ? (
              <Badge variant="demo" pulse>
                SIMULATED TELEMETRY [DEMO]
              </Badge>
            ) : (
              <Badge variant="safe" pulse>
                LIVE AIRSIM TELEMETRY
              </Badge>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time telemetry stream from AirSim multirotor local TD3 policy controller and PX4 state estimator
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="text-slate-500">FEED STATUS:</span>
          <Badge
            variant={connectionStatus === 'CONNECTED' ? 'safe' : 'danger'}
            pulse={connectionStatus === 'CONNECTED'}
          >
            {connectionStatus}
          </Badge>
        </div>
      </div>

      {/* Control Action Toolbar */}
      <SimulationControls telemetry={telemetry} />

      {/* UAV Telemetry Metrics Cards */}
      <TelemetryPanel telemetry={telemetry} />

      {/* Main Simulation Viewport (2D Radar & Camera feed placeholder) */}
      <SimulationViewport telemetry={telemetry} routePlan={currentRoutePlan} />

      {/* Mission Trajectory Progress Bar */}
      <Card
        title="Active Mission Trajectory Progress"
        subtitle={`Tracking target waypoint ${telemetry.target.waypoint_id} (${telemetry.target.waypoint_index + 1} of ${telemetry.target.total_waypoints} waypoints)`}
        icon={<Clock className="w-4 h-4 text-sky-400" />}
      >
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs font-mono">
            <span className="text-slate-400">MISSION COMPLETION:</span>
            <span className="text-sky-300 font-bold">{telemetry.mission_progress_pct}%</span>
          </div>
          <div className="w-full bg-slate-900 border border-slate-800 h-3 rounded-full overflow-hidden p-0.5">
            <div
              className="bg-gradient-to-r from-sky-500 to-emerald-400 h-full rounded-full transition-all duration-300 shadow-[0_0_8px_rgba(14,165,233,0.5)]"
              style={{ width: `${telemetry.mission_progress_pct}%` }}
            />
          </div>
        </div>
      </Card>
    </div>
  )
}
