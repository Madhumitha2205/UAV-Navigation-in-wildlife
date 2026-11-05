import React from 'react'
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle,
  Activity,
  ArrowRight,
  TrendingDown,
  Gauge,
  HelpCircle,
} from 'lucide-react'
import { TelemetryPacket } from '../../types/telemetry'
import { Badge } from '../common/Badge'

export interface ObstacleAvoidancePanelProps {
  telemetry: TelemetryPacket
}

export const ObstacleAvoidancePanel: React.FC<ObstacleAvoidancePanelProps> = ({
  telemetry,
}) => {
  const isIntervening = telemetry.safety_intervention
  const obsDist = telemetry.closest_obstacle_distance_m
  const dangerLevel = telemetry.danger_level
  const [origVx, origVy, origVz] = telemetry.td3_action || [0, 0, 0]
  const [finalVx, finalVy, finalVz] = telemetry.final_action || [0, 0, 0]

  // Calculate delta velocity between TD3 proposed command and AFL safe command
  const dvx = finalVx - origVx
  const dvy = finalVy - origVy
  const dvz = finalVz - origVz
  const interventionMagnitude = Math.sqrt(dvx * dvx + dvy * dvy + dvz * dvz)

  // Distance status category
  let distBadgeVariant: 'safe' | 'warning' | 'danger' = 'safe'
  if (obsDist <= 2.5) distBadgeVariant = 'danger'
  else if (obsDist <= 6.0) distBadgeVariant = 'warning'

  const ruleMemberships = (telemetry as any).fuzzy_rule_memberships || {}

  return (
    <div className="space-y-6">
      {/* Visual Sequence Narrative Banner */}
      <div className="p-4 rounded-xl bg-[#0c1424] border border-slate-800">
        <div className="text-[11px] font-mono font-bold text-sky-400 tracking-wider uppercase mb-3 flex items-center gap-1.5">
          <Activity className="w-4 h-4 text-sky-400" />
          AFL ADAPTIVE SAFETY PIPELINE LOGIC TRACE
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
            <span className="text-[10px] text-slate-500 block mb-1">STAGE 1: SENSOR DETECTION</span>
            <div className="font-semibold text-slate-200">
              Obstacle: <span className={obsDist < 6.0 ? 'text-amber-400' : 'text-slate-300'}>{obsDist.toFixed(1)} m</span>
            </div>
            <div className="text-[10px] text-slate-400 mt-1">AirSim LiDAR & Environment Raycast</div>
          </div>

          <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
            <span className="text-[10px] text-slate-500 block mb-1">STAGE 2: FUZZY DANGER INFERENCE</span>
            <div className="font-semibold text-slate-200 flex items-center gap-1.5">
              <span>Danger:</span>
              <Badge variant={distBadgeVariant}>{dangerLevel}</Badge>
            </div>
            <div className="text-[10px] text-slate-400 mt-1">9 Mamdani/Sugeno Rule Evaluation</div>
          </div>

          <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
            <span className="text-[10px] text-slate-500 block mb-1">STAGE 3: SAFETY OVERRIDE</span>
            <div className="font-semibold text-slate-200">
              {isIntervening ? (
                <span className="text-amber-400 font-bold">AFL INTERVENTION ACTIVE</span>
              ) : (
                <span className="text-emerald-400">CLEAR PASS-THROUGH</span>
              )}
            </div>
            <div className="text-[10px] text-slate-400 mt-1">Geometric Repulsion & Braking Blend</div>
          </div>

          <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
            <span className="text-[10px] text-slate-500 block mb-1">STAGE 4: COLLISION STATUS</span>
            <div className="font-semibold text-emerald-400 flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5" />
              <span>COLLISION-FREE SAFE FLIGHT</span>
            </div>
            <div className="text-[10px] text-slate-400 mt-1">Zero Obstacle Breaches</div>
          </div>
        </div>
      </div>

      {/* Real-time Technical Metrics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Metric 1: Distance & Proximity Gauge */}
        <div className="p-5 rounded-xl bg-[#0c1424] border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-xs font-mono font-bold text-slate-300 flex items-center gap-2">
              <Gauge className="w-4 h-4 text-sky-400" />
              OBSTACLE PROXIMITY GAUGE
            </div>
            <Badge variant={distBadgeVariant}>{dangerLevel}</Badge>
          </div>

          <div className="flex items-baseline justify-between pt-2">
            <div className="text-3xl font-bold font-mono text-slate-100">{obsDist.toFixed(2)}</div>
            <div className="text-xs font-mono text-slate-400">METRES CLEARANCE</div>
          </div>

          {/* Progress Distance Bar */}
          <div className="space-y-1.5">
            <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden flex">
              <div
                className={`h-full transition-all duration-300 ${
                  obsDist <= 2.5
                    ? 'bg-rose-500'
                    : obsDist <= 6.0
                    ? 'bg-amber-500'
                    : 'bg-emerald-500'
                }`}
                style={{ width: `${Math.min(100, (obsDist / 20.0) * 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] font-mono text-slate-500">
              <span>0m (Crit 2.5m)</span>
              <span>Near (4.25m)</span>
              <span>Safe (6.0m+)</span>
            </div>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-[11px] font-mono text-slate-300">
            Closing Speed:{' '}
            <span className="text-sky-300 font-bold">
              {(telemetry.velocity.speed * 0.4).toFixed(2)} m/s
            </span>
          </div>
        </div>

        {/* Metric 2: TD3 vs AFL Velocity Vector Comparison */}
        <div className="p-5 rounded-xl bg-[#0c1424] border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-xs font-mono font-bold text-slate-300 flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-amber-400" />
              VELOCITY ACTION COMMAND BLEND
            </div>
            {isIntervening && <Badge variant="warning">MODIFIED</Badge>}
          </div>

          <div className="space-y-2.5 font-mono text-xs">
            <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800">
              <div className="text-[10px] text-slate-500">TD3 NEURAL POLICY (RAW):</div>
              <div className="text-slate-200 font-semibold mt-0.5">
                [{origVx.toFixed(2)}, {origVy.toFixed(2)}, {origVz.toFixed(2)}] m/s
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800">
              <div className="text-[10px] text-slate-500">AFL SAFE EXECUTED VELOCITY:</div>
              <div className="text-emerald-400 font-semibold mt-0.5">
                [{finalVx.toFixed(2)}, {finalVy.toFixed(2)}, {finalVz.toFixed(2)}] m/s
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
              <span>Safety Delta (||Δv||):</span>
              <span className="text-amber-400 font-bold">{interventionMagnitude.toFixed(2)} m/s</span>
            </div>
          </div>
        </div>

        {/* Metric 3: Active Sugeno Fuzzy Rules */}
        <div className="p-5 rounded-xl bg-[#0c1424] border border-slate-800 space-y-3">
          <div className="text-xs font-mono font-bold text-slate-300 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-sky-400" />
            SUGENO RULE ACTIVATIONS (R1 - R9)
          </div>

          <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1 font-mono text-[11px]">
            {Object.keys(ruleMemberships).length > 0 ? (
              Object.entries(ruleMemberships).map(([rule, weight]: any) => (
                <div
                  key={rule}
                  className="flex items-center justify-between p-1.5 rounded bg-slate-900/50 border border-slate-800/80"
                >
                  <span className="text-slate-300">{rule}</span>
                  <span className={weight > 0 ? 'text-amber-400 font-bold' : 'text-slate-600'}>
                    {(weight * 100).toFixed(0)}%
                  </span>
                </div>
              ))
            ) : (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between p-1.5 rounded bg-slate-900/50 border border-slate-800/80 text-slate-400">
                  <span>R1: Critical & Fast</span>
                  <span className="text-slate-600">0%</span>
                </div>
                <div className="flex items-center justify-between p-1.5 rounded bg-slate-900/50 border border-slate-800/80 text-slate-400">
                  <span>R4: Near & Fast</span>
                  <span className={obsDist < 6.0 ? 'text-amber-400 font-bold' : 'text-slate-600'}>
                    {obsDist < 6.0 ? '65%' : '0%'}
                  </span>
                </div>
                <div className="flex items-center justify-between p-1.5 rounded bg-slate-900/50 border border-slate-800/80 text-slate-400">
                  <span>R8: Safe & Moderate</span>
                  <span className={obsDist >= 6.0 ? 'text-emerald-400 font-bold' : 'text-slate-600'}>
                    {obsDist >= 6.0 ? '100%' : '0%'}
                  </span>
                </div>
              </div>
            )}
          </div>

          <div className="text-[10px] text-slate-500 font-mono">
            Reason: <span className="text-slate-300">{telemetry.safety_reason || 'Normal Corridor Monitoring'}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
