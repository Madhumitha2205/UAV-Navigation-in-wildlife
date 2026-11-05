import React from 'react'
import { ShieldAlert, Activity, FileText } from 'lucide-react'
import { useTelemetryStore } from '../store/telemetryStore'
import { useSettingsStore } from '../store/settingsStore'
import { ObstacleAvoidancePanel } from '../components/safety/ObstacleAvoidancePanel'
import { SafetyHistoryTable } from '../components/safety/SafetyHistoryTable'
import { MOCK_SAFETY_EVENTS } from '../mock/mockTelemetry'
import { Badge } from '../components/common/Badge'

export const SafetyMonitoringPage: React.FC = () => {
  const { telemetry } = useTelemetryStore()
  const { demoMode } = useSettingsStore()

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-[#0c1424] border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-slate-100 tracking-wide flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-400" />
              ADAPTIVE FUZZY LOGIC (AFL) SAFETY LAYER & OBSTACLE AVOIDANCE
            </h1>
            {demoMode ? (
              <Badge variant="demo">DEMO AUDIT</Badge>
            ) : (
              <Badge variant="safe">LIVE AFL AUDIT</Badge>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time obstacle avoidance trace: Demonstrates how sensor obstacle detections trigger the Sugeno 9-rule
            fuzzy safety supervisor to modify the raw TD3 velocity commands, preventing collisions along the India flight corridor.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="text-slate-500">SUPERVISOR:</span>
          <Badge variant="safe">AFL ENGINE ACTIVE</Badge>
        </div>
      </div>

      {/* Technical Obstacle Avoidance Narrative & Metrics Panel (Requirement 5) */}
      <ObstacleAvoidancePanel telemetry={telemetry} />

      {/* Safety Interventions Historical Audit Log */}
      <SafetyHistoryTable events={MOCK_SAFETY_EVENTS} />
    </div>
  )
}
