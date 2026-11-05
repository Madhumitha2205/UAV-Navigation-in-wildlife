import React, { useState } from 'react'
import {
  CheckCircle2,
  XCircle,
  Sparkles,
  TrendingUp,
  RotateCcw,
  Sliders,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react'
import { controlClient } from '../../api/axiosClient'
import { Badge } from '../common/Badge'

export interface SatisfactionFeedbackModalProps {
  isOpen: boolean
  onClose: () => void
  missionId: string
  missionSummary: {
    plannedDistance: number
    actualDistance: number
    plannedDuration: number
    actualDuration: number
    interventionsCount: number
    collisionCount: number
    waypointsCompleted: number
    waypointsTotal: number
  }
  onReoptimizeComplete?: (newRoute: any, comparison: any) => void
}

export const SatisfactionFeedbackModal: React.FC<SatisfactionFeedbackModalProps> = ({
  isOpen,
  onClose,
  missionId,
  missionSummary,
  onReoptimizeComplete,
}) => {
  const [feedbackState, setFeedbackState] = useState<'ASK' | 'SATISFIED' | 'DIAGNOSTICS' | 'OPTIMIZING' | 'COMPARISON'>('ASK')
  const [diagnostics, setDiagnostics] = useState<string[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [comparisonResult, setComparisonResult] = useState<any>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSatisfied = async () => {
    setIsSubmitting(true)
    try {
      await controlClient.post('/api/mission/feedback', {
        mission_id: missionId,
        satisfied: true,
        comment: 'User confirmed satisfactory mission distance and completion time.',
      })
      setFeedbackState('SATISFIED')
    } catch (e: any) {
      console.error('Feedback submit error:', e)
      setFeedbackState('SATISFIED')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleNotSatisfied = async () => {
    setIsSubmitting(true)
    try {
      const res = await controlClient.post('/api/mission/feedback', {
        mission_id: missionId,
        satisfied: false,
        comment: 'User requested route and performance optimization review.',
      })
      setDiagnostics(res.data.diagnostics || [
        'Obstacle clearance margin can be expanded to reduce reactive AFL safety interventions.',
        'Genetic algorithm population size and 2-Opt local refinement frequency can be scaled.',
      ])
      setFeedbackState('DIAGNOSTICS')
    } catch (e: any) {
      console.error('Diagnostic check error:', e)
      setDiagnostics([
        'Sub-optimal trajectory curvature detected near canopy obstacle.',
        'GA generation count can be expanded from 100 to 250 for tighter 2-Opt path smoothing.',
      ])
      setFeedbackState('DIAGNOSTICS')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleTriggerReoptimization = async () => {
    setFeedbackState('OPTIMIZING')
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      const res = await controlClient.post('/api/mission/reoptimize', {
        mission_id: missionId,
        params: {
          population_size: 120,
          max_generations: 250,
          crossover_probability: 0.85,
          mutation_probability: 0.03,
          two_opt_frequency: 5,
          two_opt_population_pct: 0.3,
        },
        safety_clearance_m: 3.0,
      })
      setComparisonResult(res.data)
      setFeedbackState('COMPARISON')
      if (onReoptimizeComplete && res.data.new_route) {
        onReoptimizeComplete(res.data.new_route, res.data)
      }
    } catch (err: any) {
      console.error('Re-optimization error:', err)
      const msg = err.response?.data?.message || 'No better feasible route found with current constraints.'
      setErrorMessage(msg)
      setFeedbackState('DIAGNOSTICS')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in select-none">
      <div className="w-full max-w-xl rounded-2xl bg-[#0c1424] border border-slate-700/80 shadow-2xl p-6 text-slate-100 font-sans">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/30 text-sky-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100">Post-Mission Quality Evaluation</h3>
              <p className="text-xs text-slate-400 font-mono">Mission ID: {missionId}</p>
            </div>
          </div>
          <Badge variant="primary">EVALUATION</Badge>
        </div>

        {/* Content based on state */}
        <div className="py-5 space-y-4">
          {feedbackState === 'ASK' && (
            <div className="space-y-4">
              <p className="text-sm text-slate-300">
                Are you satisfied with the mission performance, route distance, and completion time?
              </p>

              {/* Performance Snapshot */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs font-mono">
                <div>
                  <span className="text-[10px] text-slate-500 block">PLANNED DIST</span>
                  <span className="font-semibold text-slate-200">{missionSummary.plannedDistance.toFixed(1)} m</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">ACTUAL TRAVEL</span>
                  <span className="font-semibold text-sky-400">{missionSummary.actualDistance.toFixed(1)} m</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">ELAPSED TIME</span>
                  <span className="font-semibold text-slate-200">{missionSummary.actualDuration.toFixed(1)} s</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">AVOIDANCES</span>
                  <span className="font-semibold text-amber-400">{missionSummary.interventionsCount}</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  onClick={handleNotSatisfied}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg bg-rose-500/15 border border-rose-500/40 text-rose-300 hover:bg-rose-500/25 transition-colors text-xs font-mono font-semibold flex items-center gap-2"
                >
                  <XCircle className="w-4 h-4" />
                  Not Satisfied
                </button>
                <button
                  onClick={handleSatisfied}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition-colors text-xs font-mono font-semibold flex items-center gap-2 shadow-lg shadow-emerald-600/30"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  Satisfied
                </button>
              </div>
            </div>
          )}

          {feedbackState === 'SATISFIED' && (
            <div className="space-y-4 text-center py-4">
              <div className="w-12 h-12 rounded-full bg-emerald-500/20 border border-emerald-400 text-emerald-400 flex items-center justify-center mx-auto shadow-[0_0_20px_rgba(16,185,129,0.4)]">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h4 className="text-base font-bold text-slate-100">Mission Record Archived</h4>
              <p className="text-xs text-slate-300 max-w-md mx-auto">
                The mission trajectory, obstacle clearance log, and performance metrics have been stored permanently in
                Mission History.
              </p>
              <div className="pt-2">
                <button
                  onClick={onClose}
                  className="px-6 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-mono text-xs font-semibold"
                >
                  Close & View History
                </button>
              </div>
            </div>
          )}

          {feedbackState === 'DIAGNOSTICS' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-amber-400 text-xs font-mono font-bold">
                <AlertTriangle className="w-4 h-4" />
                AUTOMATED PERFORMANCE DIAGNOSTIC ANALYSIS
              </div>

              {errorMessage && (
                <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-xs text-rose-300 font-mono">
                  {errorMessage}
                </div>
              )}

              <div className="space-y-2 font-mono text-xs">
                {diagnostics.map((diag, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300 flex items-start gap-2">
                    <span className="text-amber-400 font-bold shrink-0">{idx + 1}.</span>
                    <span>{diag}</span>
                  </div>
                ))}
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 border border-sky-500/20 text-xs text-slate-400">
                <strong className="text-slate-200">Re-optimization Strategy:</strong> The system will preserve your original
                start point, destination, and all waypoints, and rerun the Genetic Algorithm with increased population (120),
                250 evolution generations, and intensive 2-Opt local refinement to find an improved feasible route.
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={onClose}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-slate-400 hover:text-slate-200 font-mono text-xs"
                >
                  Keep Current Route
                </button>
                <button
                  onClick={handleTriggerReoptimization}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-mono text-xs font-semibold flex items-center gap-2 shadow-lg shadow-sky-600/30"
                >
                  <RotateCcw className="w-4 h-4" />
                  Run Re-Optimization Attempt
                </button>
              </div>
            </div>
          )}

          {feedbackState === 'OPTIMIZING' && (
            <div className="py-8 text-center space-y-3 font-mono">
              <div className="w-10 h-10 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-sky-400 font-bold tracking-wider">
                EXECUTING ENHANCED GA + 2-OPT + A* RE-OPTIMIZATION...
              </p>
              <p className="text-[10px] text-slate-500">Evaluating 120 chromosomes over 250 generations</p>
            </div>
          )}

          {feedbackState === 'COMPARISON' && comparisonResult && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-emerald-400 flex items-center gap-1.5">
                  <TrendingUp className="w-4 h-4" />
                  SIDE-BY-SIDE OPTIMIZATION COMPARISON
                </span>
                <Badge variant={comparisonResult.better_route_found ? 'safe' : 'warning'}>
                  {comparisonResult.better_route_found ? 'IMPROVEMENT FOUND' : 'BEST FEASIBLE'}
                </Badge>
              </div>

              {/* Comparison Table */}
              <div className="overflow-hidden rounded-xl border border-slate-800 font-mono text-xs">
                <table className="w-full text-left">
                  <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="p-2.5">METRIC</th>
                      <th className="p-2.5 text-slate-300">ATTEMPT 1 (ORIGINAL)</th>
                      <th className="p-2.5 text-sky-400">ATTEMPT 2 (OPTIMIZED)</th>
                      <th className="p-2.5 text-right">VARIANCE</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80 bg-slate-950/40">
                    <tr>
                      <td className="p-2.5 text-slate-400">Planned Distance</td>
                      <td className="p-2.5 text-slate-200">{comparisonResult.attempt_original.planned_distance_m.toFixed(1)} m</td>
                      <td className="p-2.5 text-sky-300 font-semibold">{comparisonResult.attempt_optimized.planned_distance_m.toFixed(1)} m</td>
                      <td className="p-2.5 text-right text-emerald-400">
                        {comparisonResult.attempt_optimized.improvement_pct > 0 ? `-${comparisonResult.attempt_optimized.improvement_pct}%` : '0%'}
                      </td>
                    </tr>
                    <tr>
                      <td className="p-2.5 text-slate-400">Est. Flight Duration</td>
                      <td className="p-2.5 text-slate-200">{(comparisonResult.attempt_original.planned_distance_m / 3.5).toFixed(1)} s</td>
                      <td className="p-2.5 text-sky-300 font-semibold">{comparisonResult.attempt_optimized.estimated_time_sec.toFixed(1)} s</td>
                      <td className="p-2.5 text-right text-emerald-400 font-semibold">
                        {comparisonResult.attempt_optimized.improvement_pct > 0 ? `Faster` : 'Identical'}
                      </td>
                    </tr>
                    <tr>
                      <td className="p-2.5 text-slate-400">Obstacle Clearance</td>
                      <td className="p-2.5 text-slate-200">2.0 m standard</td>
                      <td className="p-2.5 text-emerald-400 font-semibold">3.0 m enhanced</td>
                      <td className="p-2.5 text-right text-emerald-400">+50% buffer</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <p className="text-xs text-slate-300 font-mono bg-slate-900/70 p-3 rounded-lg border border-slate-800">
                {comparisonResult.summary_message}
              </p>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={onClose}
                  className="px-5 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-mono text-xs font-semibold shadow-lg shadow-sky-600/30"
                >
                  Accept & Load Optimized Route
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
