import React from 'react'
import { ArrowRight, Cpu, Shield, AlertCircle } from 'lucide-react'
import { TelemetryPacket } from '../../types/telemetry'
import { Card } from '../common/Card'
import { Badge } from '../common/Badge'

export interface ActionComparisonProps {
  telemetry: TelemetryPacket
}

export const ActionComparison: React.FC<ActionComparisonProps> = ({ telemetry }) => {
  const { td3_action, final_action, safety_intervention, safety_reason } = telemetry

  // Compute difference magnitude
  const dx = final_action[0] - td3_action[0]
  const dy = final_action[1] - td3_action[1]
  const dz = final_action[2] - td3_action[2]
  const deltaMag = Math.sqrt(dx * dx + dy * dy + dz * dz)

  return (
    <Card
      title="TD3 Policy vs Adaptive Fuzzy Safety Action Modification"
      subtitle="Dynamic collision avoidance command blending via Part 2 safety layer"
      icon={<Cpu className="w-4 h-4 text-cyan-400" />}
    >
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
          {/* TD3 Proposed Velocity */}
          <div className="p-3.5 bg-slate-900/80 border border-slate-800 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono font-semibold text-sky-400 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5" />
                TD3 PROPOSED ACTION
              </span>
              <span className="text-[10px] text-slate-500 font-mono">[vx, vy, vz] m/s</span>
            </div>
            <div className="text-lg font-mono font-bold text-slate-100">
              [{td3_action[0].toFixed(2)}, {td3_action[1].toFixed(2)}, {td3_action[2].toFixed(2)}]
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Raw neural network policy output
            </div>
          </div>

          {/* Transformation Delta Vector */}
          <div className="flex flex-col items-center justify-center text-center p-2">
            <div className="flex items-center gap-2 text-slate-400 font-mono text-xs mb-1">
              <span>AFL FILTER</span>
              <ArrowRight className="w-4 h-4 text-amber-400" />
            </div>
            <Badge
              variant={safety_intervention ? 'warning' : 'safe'}
              className="text-xs font-mono py-1 px-3"
            >
              Δ Mag: {deltaMag.toFixed(2)} m/s
            </Badge>
            <span className="text-[10px] text-slate-500 mt-1">
              {safety_intervention ? 'Fuzzy repulsion & brake active' : 'Zero intervention pass-through'}
            </span>
          </div>

          {/* AFL Safety Adjusted Action */}
          <div className="p-3.5 bg-slate-900/80 border border-slate-800 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono font-semibold text-emerald-400 flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5" />
                FINAL APPLIED ACTION
              </span>
              <span className="text-[10px] text-slate-500 font-mono">[vx, vy, vz] m/s</span>
            </div>
            <div className="text-lg font-mono font-bold text-emerald-400">
              [{final_action[0].toFixed(2)}, {final_action[1].toFixed(2)}, {final_action[2].toFixed(2)}]
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Safe command sent to AirSim multirotor
            </div>
          </div>
        </div>

        {/* Reason / Alert */}
        {safety_reason && (
          <div className="flex items-center gap-2 p-3 bg-amber-950/30 border border-amber-800/60 rounded-lg text-xs text-amber-300">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Intervention Trigger:</strong> {safety_reason}
            </span>
          </div>
        )}
      </div>
    </Card>
  )
}
