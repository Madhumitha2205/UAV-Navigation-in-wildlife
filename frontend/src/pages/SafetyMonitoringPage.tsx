import React from 'react'
import { ShieldAlert, Activity, FileText } from 'lucide-react'
import { useTelemetryStore } from '../store/telemetryStore'
import { useSettingsStore } from '../store/settingsStore'
import { SafetyStatus } from '../components/safety/SafetyStatus'
import { ActionComparison } from '../components/safety/ActionComparison'
import { ObstacleVisualization } from '../components/safety/ObstacleVisualization'
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
              ADAPTIVE FUZZY LOGIC (AFL) SAFETY LAYER
            </h1>
            {demoMode ? (
              <Badge variant="demo">DEMO AUDIT</Badge>
            ) : (
              <Badge variant="safe">LIVE AFL AUDIT</Badge>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Dynamic safety supervisor intervening between local TD3 neural network policy and AirSim multirotor motors
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="text-slate-500">SUPERVISOR:</span>
          <Badge variant="safe">AFL ENGINE ACTIVE</Badge>
        </div>
      </div>

      {/* Safety Status Cards */}
      <SafetyStatus telemetry={telemetry} />

      {/* Action Modification Comparison */}
      <ActionComparison telemetry={telemetry} />

      {/* Proximity Radar & Distance Zones */}
      <ObstacleVisualization telemetry={telemetry} />

      {/* Safety Interventions History Table */}
      <SafetyHistoryTable events={MOCK_SAFETY_EVENTS} />
    </div>
  )
}
