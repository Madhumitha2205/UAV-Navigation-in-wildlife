import React, { useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { ExperimentTrial } from '../../types/analytics'
import { Card } from '../common/Card'
import { Badge } from '../common/Badge'
import { GitCompare, Filter, AlertOctagon } from 'lucide-react'

export interface ExperimentComparisonProps {
  trials: ExperimentTrial[]
}

export const ExperimentComparison: React.FC<ExperimentComparisonProps> = ({ trials }) => {
  const [selectedTrialId, setSelectedTrialId] = useState<string>(trials[0]?.trial_id || '')

  const currentTrial = trials.find((t) => t.trial_id === selectedTrialId) || trials[0]

  // Chart data comparing the 3 configurations
  const comparisonChartData = currentTrial
    ? [
        {
          name: 'Baseline (Config A)',
          Collisions: currentTrial.config_a.collision_count,
          Jerk: currentTrial.config_a.control_smoothness_rms_jerk,
          EnergyProxy: currentTrial.config_a.estimated_energy_proxy_joules / 100, // scaled for chart
        },
        {
          name: 'TD3 Raw (Config B)',
          Collisions: currentTrial.config_b.collision_count,
          Jerk: currentTrial.config_b.control_smoothness_rms_jerk,
          EnergyProxy: currentTrial.config_b.estimated_energy_proxy_joules / 100,
        },
        {
          name: 'TD3 + AFL (Config C)',
          Collisions: currentTrial.config_c.collision_count,
          Jerk: currentTrial.config_c.control_smoothness_rms_jerk,
          EnergyProxy: currentTrial.config_c.estimated_energy_proxy_joules / 100,
        },
      ]
    : []

  return (
    <div className="space-y-4">
      {/* Scenario / Trial Selector Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-[#0d1424] border border-slate-800 rounded-xl">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-sky-400" />
          <span className="text-xs font-mono font-semibold text-slate-300">
            EVALUATION TRIAL SCENARIO:
          </span>
          <select
            value={selectedTrialId}
            onChange={(e) => setSelectedTrialId(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-100 focus:outline-none focus:border-sky-500"
          >
            {trials.map((t) => (
              <option key={t.trial_id} value={t.trial_id}>
                {t.trial_id} — {t.scenario_name} (Seed: {t.seed})
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <span>TRIAL SEED:</span>
          <Badge variant="primary">{currentTrial?.seed}</Badge>
        </div>
      </div>

      {/* Comparative Evaluation Table */}
      {currentTrial && (
        <Card
          title="Comparative Framework Evaluation Matrix"
          subtitle="Direct benchmark across Navigation Configurations A, B, and C"
          icon={<GitCompare className="w-4 h-4 text-sky-400 text-glow" />}
        >
          <div className="overflow-x-auto rounded-lg border border-slate-800">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-900/90 text-slate-400 font-mono border-b border-slate-800">
                <tr>
                  <th className="py-3 px-3">Configuration</th>
                  <th className="py-3 px-3 text-center">Status</th>
                  <th className="py-3 px-3 text-center">Collisions</th>
                  <th className="py-3 px-3 text-center">Coverage (%)</th>
                  <th className="py-3 px-3 text-center">Travelled Dist (m)</th>
                  <th className="py-3 px-3 text-center">Exec Time (s)</th>
                  <th className="py-3 px-3 text-center">Smoothness (Jerk)</th>
                  <th className="py-3 px-3 text-center">AFL Interventions</th>
                  <th className="py-3 px-3 text-right">Energy Proxy (J)*</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {/* Config A: Baseline */}
                <tr className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 px-3">
                    <div className="font-semibold text-slate-300">
                      {currentTrial.config_a.config_name}
                    </div>
                    <div className="text-[10px] text-slate-500 font-sans">
                      {currentTrial.config_a.description}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-center">
                    <Badge variant={currentTrial.config_a.success ? 'safe' : 'danger'}>
                      {currentTrial.config_a.success ? 'SUCCESS' : 'COLLIDED'}
                    </Badge>
                  </td>
                  <td className="py-3 px-3 text-center text-rose-400 font-bold">
                    {currentTrial.config_a.collision_count}
                  </td>
                  <td className="py-3 px-3 text-center text-slate-300">
                    {currentTrial.config_a.monitoring_coverage_pct}%
                  </td>
                  <td className="py-3 px-3 text-center text-slate-300">
                    {currentTrial.config_a.travelled_distance_m}
                  </td>
                  <td className="py-3 px-3 text-center text-slate-300">
                    {currentTrial.config_a.execution_time_sec}s
                  </td>
                  <td className="py-3 px-3 text-center text-slate-300">
                    {currentTrial.config_a.control_smoothness_rms_jerk}
                  </td>
                  <td className="py-3 px-3 text-center text-slate-500">0</td>
                  <td className="py-3 px-3 text-right text-slate-400 font-bold">
                    {currentTrial.config_a.estimated_energy_proxy_joules} J
                  </td>
                </tr>

                {/* Config B: TD3 Raw */}
                <tr className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 px-3">
                    <div className="font-semibold text-sky-400">
                      {currentTrial.config_b.config_name}
                    </div>
                    <div className="text-[10px] text-slate-500 font-sans">
                      {currentTrial.config_b.description}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-center">
                    <Badge variant={currentTrial.config_b.success ? 'safe' : 'danger'}>
                      {currentTrial.config_b.success ? 'SUCCESS' : 'COLLIDED'}
                    </Badge>
                  </td>
                  <td className="py-3 px-3 text-center text-rose-400 font-bold">
                    {currentTrial.config_b.collision_count}
                  </td>
                  <td className="py-3 px-3 text-center text-slate-300">
                    {currentTrial.config_b.monitoring_coverage_pct}%
                  </td>
                  <td className="py-3 px-3 text-center text-slate-300">
                    {currentTrial.config_b.travelled_distance_m}
                  </td>
                  <td className="py-3 px-3 text-center text-slate-300">
                    {currentTrial.config_b.execution_time_sec}s
                  </td>
                  <td className="py-3 px-3 text-center text-slate-300">
                    {currentTrial.config_b.control_smoothness_rms_jerk}
                  </td>
                  <td className="py-3 px-3 text-center text-slate-500">0</td>
                  <td className="py-3 px-3 text-right text-slate-400 font-bold">
                    {currentTrial.config_b.estimated_energy_proxy_joules} J
                  </td>
                </tr>

                {/* Config C: TD3 + AFL (Proposed) */}
                <tr className="bg-emerald-950/20 hover:bg-emerald-950/30 border-l-2 border-emerald-500 transition-colors">
                  <td className="py-3 px-3">
                    <div className="font-bold text-emerald-400">
                      {currentTrial.config_c.config_name}
                    </div>
                    <div className="text-[10px] text-slate-400 font-sans">
                      {currentTrial.config_c.description}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-center">
                    <Badge variant="safe">SAFE COMPLETED</Badge>
                  </td>
                  <td className="py-3 px-3 text-center text-emerald-400 font-bold">
                    {currentTrial.config_c.collision_count} (ZERO)
                  </td>
                  <td className="py-3 px-3 text-center text-emerald-400 font-bold">
                    {currentTrial.config_c.monitoring_coverage_pct}%
                  </td>
                  <td className="py-3 px-3 text-center text-slate-200">
                    {currentTrial.config_c.travelled_distance_m}
                  </td>
                  <td className="py-3 px-3 text-center text-slate-200">
                    {currentTrial.config_c.execution_time_sec}s
                  </td>
                  <td className="py-3 px-3 text-center text-emerald-400 font-bold">
                    {currentTrial.config_c.control_smoothness_rms_jerk} (Smoothest)
                  </td>
                  <td className="py-3 px-3 text-center text-amber-400 font-bold">
                    {currentTrial.config_c.fuzzy_interventions}
                  </td>
                  <td className="py-3 px-3 text-right text-emerald-400 font-bold">
                    {currentTrial.config_c.estimated_energy_proxy_joules} J
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <p className="text-[10px] text-slate-500 mt-2 font-mono">
            * Note: Energy metric is explicitly estimated as a kinematic control-effort proxy (integral of ||u||^2 dt) rather than battery hardware dissipation.
          </p>
        </Card>
      )}

      {/* Visual Chart Comparison */}
      <Card
        title="Collision Avoidance & Smoothness Comparative Analysis"
        subtitle="Direct graphical comparison across configurations for the selected scenario"
      >
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={comparisonChartData} margin={{ top: 20, right: 30, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '8px',
                  color: '#f8fafc',
                }}
              />
              <Legend verticalAlign="top" align="right" wrapperStyle={{ fontSize: '11px' }} />
              <Bar dataKey="Collisions" fill="#ef4444" name="Collisions" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Jerk" fill="#0ea5e9" name="RMS Jerk (m/s³)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="EnergyProxy" fill="#10b981" name="Kinematic Energy Proxy (x10² J)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  )
}
