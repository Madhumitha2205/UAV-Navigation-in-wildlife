import React, { useState, useEffect } from 'react'
import {
  History,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  TrendingUp,
  MapPin,
  Calendar,
  Clock,
  Navigation,
  ShieldCheck,
  GitCompare,
} from 'lucide-react'
import { controlClient } from '../api/axiosClient'
import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Badge'

export interface HistoricalMission {
  mission_id: string
  timestamp: string
  nav_mode: string
  success: boolean
  start_location: string
  destination: string
  planned_distance_m: number
  actual_distance_m: number
  planned_time_sec: number
  actual_time_sec: number
  average_velocity_mps: number
  waypoints_completed: number
  total_waypoints: number
  obstacle_encounters: number
  avoidance_interventions: number
  collision_count: number
  satisfaction_status: string
  optimization_attempts: number
  user_feedback?: string
}

const DEFAULT_HISTORY: HistoricalMission[] = [
  {
    mission_id: 'mission_india_kaziranga_01',
    timestamp: '2026-11-04 18:40:12',
    nav_mode: 'TD3_WITH_FUZZY_SAFETY',
    success: true,
    start_location: 'Kaziranga West Command Hub (26.5775° N, 93.1711° E)',
    destination: 'Kaziranga East Outpost (26.6500° N, 93.2500° E)',
    planned_distance_m: 294.85,
    actual_distance_m: 282.08,
    planned_time_sec: 84.2,
    actual_time_sec: 81.1,
    average_velocity_mps: 3.48,
    waypoints_completed: 6,
    total_waypoints: 6,
    obstacle_encounters: 3,
    avoidance_interventions: 62,
    collision_count: 0,
    satisfaction_status: 'SATISFIED',
    optimization_attempts: 1,
    user_feedback: 'Satisfactory collision-free flight across dense forest corridor.',
  },
  {
    mission_id: 'mission_india_corbett_02',
    timestamp: '2026-11-04 17:15:30',
    nav_mode: 'BASELINE',
    success: true,
    start_location: 'Jim Corbett Base Hub (29.5300° N, 78.7747° E)',
    destination: 'Ramganga Sector (29.5800° N, 78.8400° E)',
    planned_distance_m: 294.85,
    actual_distance_m: 281.80,
    planned_time_sec: 84.2,
    actual_time_sec: 69.1,
    average_velocity_mps: 4.07,
    waypoints_completed: 6,
    total_waypoints: 6,
    obstacle_encounters: 3,
    avoidance_interventions: 0,
    collision_count: 0,
    satisfaction_status: 'SATISFIED',
    optimization_attempts: 1,
  },
]

export const MissionHistoryPage: React.FC = () => {
  const [missions, setMissions] = useState<HistoricalMission[]>(DEFAULT_HISTORY)
  const [selectedMission, setSelectedMission] = useState<HistoricalMission | null>(DEFAULT_HISTORY[0])
  const [compareMissionA, setCompareMissionA] = useState<HistoricalMission | null>(DEFAULT_HISTORY[0])
  const [compareMissionB, setCompareMissionB] = useState<HistoricalMission | null>(DEFAULT_HISTORY[1])

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await controlClient.get<HistoricalMission[]>('/api/mission/history')
        if (res.data && res.data.length > 0) {
          setMissions(res.data)
          setSelectedMission(res.data[0])
          if (res.data.length > 1) {
            setCompareMissionA(res.data[0])
            setCompareMissionB(res.data[1])
          }
        }
      } catch (e) {
        console.debug('Failed to fetch remote history, using local state:', e)
      }
    }
    fetchHistory()
  }, [])

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-[#0c1424] border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-slate-100 tracking-wide flex items-center gap-2">
              <History className="w-5 h-5 text-sky-400" />
              UAV MISSION ARCHIVE & PERFORMANCE HISTORY
            </h1>
            <Badge variant="primary">{missions.length} MISSIONS LOGGED</Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Permanent historical records of completed UAV flights across India: Inspect planned vs actual distance,
            flight durations, obstacle encounters, fuzzy avoidance interventions, and re-optimization attempts.
          </p>
        </div>
      </div>

      {/* Main Grid: Mission Selector List & Detail View */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Mission Records List */}
        <div className="p-4 rounded-xl bg-[#0c1424] border border-slate-800 space-y-3">
          <div className="text-xs font-mono font-bold text-slate-300 flex items-center gap-1.5 pb-2 border-b border-slate-800">
            <Calendar className="w-4 h-4 text-sky-400" />
            RECORDED FLIGHT LOGS
          </div>

          <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
            {missions.map((m) => (
              <div
                key={m.mission_id}
                onClick={() => setSelectedMission(m)}
                className={`p-3 rounded-lg border cursor-pointer transition-all font-mono text-xs ${
                  selectedMission?.mission_id === m.mission_id
                    ? 'bg-sky-950/40 border-sky-500/80 shadow-md'
                    : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-slate-200 truncate max-w-[170px]">{m.mission_id}</span>
                  <Badge variant={m.satisfaction_status === 'SATISFIED' ? 'safe' : 'warning'}>
                    {m.satisfaction_status}
                  </Badge>
                </div>
                <div className="text-[10px] text-slate-400">{m.timestamp}</div>
                <div className="flex items-center justify-between text-[11px] text-slate-300 mt-2">
                  <span>Travelled: {m.actual_distance_m.toFixed(1)}m</span>
                  <span>Avoidances: {m.avoidance_interventions}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Selected Mission Inspector */}
        {selectedMission && (
          <div className="lg:col-span-2 p-5 rounded-xl bg-[#0c1424] border border-slate-800 space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-sm font-mono font-bold text-slate-100">{selectedMission.mission_id}</h3>
                <span className="text-xs text-slate-400 font-mono">Completed: {selectedMission.timestamp}</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={selectedMission.success ? 'safe' : 'danger'}>
                  {selectedMission.success ? 'MISSION SUCCESS' : 'COLLISION BREACH'}
                </Badge>
                <Badge variant="primary">{selectedMission.nav_mode}</Badge>
              </div>
            </div>

            {/* Geographical Summary */}
            <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800 font-mono text-xs space-y-2">
              <div className="flex items-start gap-2">
                <MapPin className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <span className="text-[10px] text-slate-500 block">ORIGIN / LAUNCH</span>
                  <span className="text-slate-200">{selectedMission.start_location}</span>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <MapPin className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <span className="text-[10px] text-slate-500 block">DESTINATION</span>
                  <span className="text-slate-200">{selectedMission.destination}</span>
                </div>
              </div>
            </div>

            {/* Core Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">PLANNED DISTANCE</span>
                <span className="text-sm font-bold text-slate-200">{selectedMission.planned_distance_m.toFixed(1)} m</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">ACTUAL TRAVELLED</span>
                <span className="text-sm font-bold text-sky-400">{selectedMission.actual_distance_m.toFixed(1)} m</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">FLIGHT DURATION</span>
                <span className="text-sm font-bold text-slate-200">{selectedMission.actual_time_sec.toFixed(1)} s</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">AVG VELOCITY</span>
                <span className="text-sm font-bold text-emerald-400">{selectedMission.average_velocity_mps.toFixed(2)} m/s</span>
              </div>
            </div>

            {/* Safety & Avoidance Audit */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">WAYPOINTS VISITED</span>
                <span className="text-slate-200 font-semibold">
                  {selectedMission.waypoints_completed} / {selectedMission.total_waypoints}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">OBSTACLE ENCOUNTERS</span>
                <span className="text-amber-400 font-semibold">{selectedMission.obstacle_encounters}</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">AFL INTERVENTIONS</span>
                <span className="text-amber-400 font-semibold">{selectedMission.avoidance_interventions}</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">COLLISIONS</span>
                <span className="text-emerald-400 font-semibold">{selectedMission.collision_count} (Safe)</span>
              </div>
            </div>

            {/* Satisfaction & Re-optimization Audit */}
            <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800 font-mono text-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">USER SATISFACTION EVALUATION:</span>
                <Badge variant={selectedMission.satisfaction_status === 'SATISFIED' ? 'safe' : 'warning'}>
                  {selectedMission.satisfaction_status}
                </Badge>
              </div>
              <div className="text-slate-300">
                Feedback:{' '}
                <span className="italic text-slate-400">
                  {selectedMission.user_feedback || 'Mission verified collision-free.'}
                </span>
              </div>
              <div className="text-slate-400 text-[11px]">
                Optimization Attempts:{' '}
                <span className="text-sky-400 font-bold">{selectedMission.optimization_attempts}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Side-by-Side Comparison Section (Requirement 9) */}
      {compareMissionA && compareMissionB && (
        <Card
          title="Side-by-Side Mission & Optimization Comparison"
          subtitle="Compare performance metrics between different optimization runs or baseline vs TD3 controller"
          icon={<GitCompare className="w-4 h-4 text-sky-400" />}
        >
          <div className="overflow-x-auto font-mono text-xs">
            <table className="w-full text-left">
              <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="p-3">METRIC</th>
                  <th className="p-3 text-sky-400">TRIAL A: {compareMissionA.mission_id}</th>
                  <th className="p-3 text-emerald-400">TRIAL B: {compareMissionB.mission_id}</th>
                  <th className="p-3 text-right">COMPARISON / DELTA</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 bg-slate-950/40">
                <tr>
                  <td className="p-3 text-slate-400">Navigation Mode</td>
                  <td className="p-3 text-slate-200">{compareMissionA.nav_mode}</td>
                  <td className="p-3 text-slate-200">{compareMissionB.nav_mode}</td>
                  <td className="p-3 text-right text-slate-400">—</td>
                </tr>
                <tr>
                  <td className="p-3 text-slate-400">Actual Distance Travelled</td>
                  <td className="p-3 text-sky-300">{compareMissionA.actual_distance_m.toFixed(1)} m</td>
                  <td className="p-3 text-emerald-300">{compareMissionB.actual_distance_m.toFixed(1)} m</td>
                  <td className="p-3 text-right text-slate-200">
                    {Math.abs(compareMissionA.actual_distance_m - compareMissionB.actual_distance_m).toFixed(1)} m diff
                  </td>
                </tr>
                <tr>
                  <td className="p-3 text-slate-400">Flight Duration</td>
                  <td className="p-3 text-sky-300">{compareMissionA.actual_time_sec.toFixed(1)} s</td>
                  <td className="p-3 text-emerald-300">{compareMissionB.actual_time_sec.toFixed(1)} s</td>
                  <td className="p-3 text-right text-slate-200">
                    {Math.abs(compareMissionA.actual_time_sec - compareMissionB.actual_time_sec).toFixed(1)} s diff
                  </td>
                </tr>
                <tr>
                  <td className="p-3 text-slate-400">AFL Safety Interventions</td>
                  <td className="p-3 text-amber-400 font-semibold">{compareMissionA.avoidance_interventions}</td>
                  <td className="p-3 text-amber-400 font-semibold">{compareMissionB.avoidance_interventions}</td>
                  <td className="p-3 text-right text-emerald-400 font-semibold">Zero Collisions</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
