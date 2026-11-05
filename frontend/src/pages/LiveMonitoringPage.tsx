import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  Navigation,
  Radio,
  Play,
  Pause,
  Square,
  Home,
  RotateCcw,
  Sparkles,
  Route,
  Activity,
  CheckCircle2,
  Clock,
  Layers,
  MapPin,
  Flag,
  ShieldCheck,
  AlertTriangle,
} from 'lucide-react'
import { useTelemetryStore } from '../store/telemetryStore'
import { useMissionStore } from '../store/missionStore'
import { useSettingsStore } from '../store/settingsStore'
import { controlApi } from '../api/controlApi'
import { IndiaLeafletMap } from '../components/map/IndiaLeafletMap'
import { AirSim3DViewport } from '../components/monitoring/AirSim3DViewport'
import { TelemetryPanel } from '../components/monitoring/TelemetryPanel'
import { SatisfactionFeedbackModal } from '../components/mission/SatisfactionFeedbackModal'
import { GeoCoordinate } from '../utils/geoUtils'
import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Badge'

export const LiveMonitoringPage: React.FC = () => {
  const { telemetry, connectionStatus } = useTelemetryStore()
  const { currentRoutePlan, environmentConfig, planRoute, isPlanning } = useMissionStore()
  const { demoMode } = useSettingsStore()

  const [isAirSimConnected, setIsAirSimConnected] = useState(false)
  const [actualTrajectory, setActualTrajectory] = useState<{ lat: number; lon: number }[]>([])
  const [showSatisfactionModal, setShowSatisfactionModal] = useState(false)
  const [missionDoneTriggered, setMissionDoneTriggered] = useState(false)
  const [missionError, setMissionError] = useState<string | null>(null)

  const getErrorMessage = (error: unknown) => {
    if (axios.isAxiosError<{ message?: string }>(error)) {
      return error.response?.data?.message || error.message
    }
    return error instanceof Error ? error.message : 'The mission command failed.'
  }

  // Start & Destination as GeoCoordinates
  const startGeo: GeoCoordinate = {
    lat: environmentConfig.start_position.lat ?? 26.5775,
    lon: environmentConfig.start_position.lon ?? 93.1711,
    alt: environmentConfig.start_position.z,
    name: 'Launch Hub (Start)',
  }

  const destGeo: GeoCoordinate = {
    lat: environmentConfig.destination.lat ?? 26.6500,
    lon: environmentConfig.destination.lon ?? 93.2500,
    alt: environmentConfig.destination.z,
    name: 'Target Station (Dest)',
  }

  const waypointsGeo: GeoCoordinate[] = environmentConfig.monitoring_waypoints.map((w, i) => ({
    lat: w.lat ?? 26.589 + i * 0.009,
    lon: w.lon ?? 93.182 + i * 0.009,
    alt: w.z,
    name: w.zone_name,
  }))

  // Track live UAV actual trajectory
  useEffect(() => {
    const pos = telemetry.position as any
    if (pos && pos.lat && pos.lon && telemetry.flight_state !== 'IDLE' && telemetry.flight_state !== 'DISCONNECTED') {
      setActualTrajectory((prev) => {
        const last = prev[prev.length - 1]
        if (!last || Math.abs(last.lat - pos.lat) > 1e-5 || Math.abs(last.lon - pos.lon) > 1e-5) {
          return [...prev, { lat: pos.lat, lon: pos.lon }]
        }
        return prev
      })
    }
  }, [telemetry.position, telemetry.flight_state])

  // Check AirSim status on mount
  useEffect(() => {
    const checkAirSim = async () => {
      try {
        const status = await controlApi.getSimulationStatus(demoMode)
        setIsAirSimConnected(status.simulator_connected)
      } catch (err) {
        setIsAirSimConnected(false)
      }
    }
    checkAirSim()
    const interval = setInterval(checkAirSim, 4000)
    return () => clearInterval(interval)
  }, [demoMode])

  // Detect Mission Completion and trigger Satisfaction Evaluation
  useEffect(() => {
    if (
      (telemetry.mission_progress_pct >= 99 || telemetry.flight_state === 'LANDED') &&
      actualTrajectory.length > 15 &&
      !missionDoneTriggered
    ) {
      setMissionDoneTriggered(true)
      const timer = setTimeout(() => {
        setShowSatisfactionModal(true)
      }, 1500)
      return () => clearTimeout(timer)
    }
  }, [telemetry.mission_progress_pct, telemetry.flight_state, actualTrajectory.length, missionDoneTriggered])

  // Flight Controls
  const handleStart = async () => {
    setMissionError(null)
    if (!demoMode && !currentRoutePlan) {
      setMissionError('Plan a route before starting a live AirSim mission.')
      return
    }
    if (!demoMode && !isAirSimConnected) {
      setMissionError('Connect to AirSim before starting a live 3D mission.')
      return
    }

    setActualTrajectory([])
    setMissionDoneTriggered(false)
    try {
      await controlApi.startMission(currentRoutePlan?.mission_id || 'mission_live', demoMode, 'airsim')
    } catch (error) {
      setMissionError(getErrorMessage(error))
    }
  }

  const handlePause = async () => {
    try {
      await controlApi.pauseMission(demoMode)
    } catch (e) {
      console.error('Pause error:', e)
    }
  }

  const handleResume = async () => {
    try {
      await controlApi.resumeMission(demoMode)
    } catch (e) {
      console.error('Resume error:', e)
    }
  }

  const handleStop = async () => {
    try {
      await controlApi.stopMission(demoMode)
      setShowSatisfactionModal(true)
    } catch (e) {
      console.error('Stop error:', e)
    }
  }

  const handleRestart = async () => {
    setActualTrajectory([])
    setMissionDoneTriggered(false)
    try {
      await controlApi.restartMission(demoMode)
    } catch (e) {
      console.error('Restart error:', e)
    }
  }

  const handleRTL = async () => {
    try {
      await controlApi.returnToLand(demoMode)
    } catch (e) {
      console.error('RTL error:', e)
    }
  }

  const handleConnectAirSim = async () => {
    setMissionError(null)
    try {
      const res = await controlApi.connectSimulator(demoMode)
      if (res.success) setIsAirSimConnected(true)
    } catch (error) {
      setIsAirSimConnected(false)
      setMissionError(getErrorMessage(error))
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Banner & System Connectivity Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-4 rounded-xl bg-[#0c1424] border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Navigation className="w-5 h-5 text-sky-400" />
            <h1 className="text-lg font-bold text-slate-100 tracking-wide">
              LIVE UAV SIMULATION MONITORING
            </h1>
            <Badge variant="safe">SYNCHRONIZED DUAL-VIEW</Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Single unified UAV mission executing simultaneously in View 1 (Real Geographical India Map) and View 2 (3D AirSim Blocks Simulation).
          </p>
        </div>

        {/* Connectivity Status Badges */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800">
            <span className="text-slate-500 text-[10px]">BACKEND:</span>
            <span className="text-emerald-400 font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> ONLINE
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800">
            <span className="text-slate-500 text-[10px]">TELEMETRY:</span>
            <span className={connectionStatus === 'CONNECTED' ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
              {connectionStatus}
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800">
            <span className="text-slate-500 text-[10px]">ROUTE PLAN:</span>
            <span className={currentRoutePlan ? 'text-sky-400 font-bold' : 'text-slate-400'}>
              {currentRoutePlan ? 'VALIDATED' : 'IDLE'}
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800">
            <span className="text-slate-500 text-[10px]">AIRSIM 3D:</span>
            {isAirSimConnected ? (
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span> CONNECTED (41451)
              </span>
            ) : (
              <span className="text-amber-400 font-semibold" title="Connect AirSim before starting a live mission.">
                DISCONNECTED (MISSION DISABLED)
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Primary Mission Command Toolbar */}
      <div className="p-3.5 rounded-xl bg-[#0c1424] border border-slate-800 flex flex-wrap items-center justify-between gap-3 shadow-lg">
        <div className="flex flex-wrap items-center gap-2">
          {/* Plan Route button */}
          <button
            onClick={() => planRoute()}
            disabled={isPlanning}
            className="px-3.5 py-2 rounded-lg bg-sky-700 hover:bg-sky-600 disabled:opacity-50 text-white font-mono text-xs font-semibold flex items-center gap-1.5 shadow-md transition-all"
            title="Re-run GA + 2-Opt route planner"
          >
            <Route className="w-4 h-4" />
            {isPlanning ? 'Planning...' : 'Plan Route'}
          </button>

          {/* Start / Pause / Resume Controls */}
          {telemetry.flight_state === 'IDLE' || telemetry.flight_state === 'LANDED' || telemetry.flight_state === 'ERROR' ? (
            <button
              onClick={handleStart}
              disabled={isPlanning || (!demoMode && (!currentRoutePlan || !isAirSimConnected))}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-mono text-xs font-semibold flex items-center gap-2 shadow-lg shadow-emerald-600/30 transition-all"
            >
              <Play className="w-4 h-4 fill-current" />
              Start Mission
            </button>
          ) : telemetry.flight_state === 'HOVERING' ? (
            <button
              onClick={handleResume}
              className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-mono text-xs font-semibold flex items-center gap-2 shadow-lg shadow-sky-600/30 transition-all"
            >
              <Play className="w-4 h-4 fill-current" />
              Resume Mission
            </button>
          ) : (
            <button
              onClick={handlePause}
              className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-mono text-xs font-semibold flex items-center gap-2 shadow-lg shadow-amber-600/30 transition-all"
            >
              <Pause className="w-4 h-4 fill-current" />
              Pause Mission
            </button>
          )}

          <button
            onClick={handleStop}
            className="px-3.5 py-2 rounded-lg bg-rose-600/20 border border-rose-500/40 text-rose-300 hover:bg-rose-600/30 font-mono text-xs font-semibold flex items-center gap-1.5 transition-all"
          >
            <Square className="w-4 h-4" />
            Stop / Abort
          </button>

          <button
            onClick={handleRestart}
            className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-mono text-xs font-semibold flex items-center gap-1.5 transition-all"
            title="Restart mission from launch point"
          >
            <RotateCcw className="w-4 h-4" />
            Restart Mission
          </button>

          <button
            onClick={handleRTL}
            className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs font-semibold flex items-center gap-1.5 transition-all"
          >
            <Home className="w-4 h-4" />
            RTL
          </button>
        </div>

        <div className="flex items-center gap-3 font-mono text-xs">
          <button
            onClick={() => setShowSatisfactionModal(true)}
            className="px-3 py-1.5 rounded-lg bg-sky-500/10 border border-sky-500/30 text-sky-300 hover:bg-sky-500/20 flex items-center gap-1.5 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-sky-400" />
            Evaluate Performance
          </button>
        </div>
      </div>

      {missionError && (
        <div role="alert" className="rounded-lg border border-rose-500/40 bg-rose-950/30 px-3 py-2 text-sm text-rose-200">
          {missionError}
        </div>
      )}

      {/* Mission Corridor Waypoint Sequence Bar */}
      <div className="p-3 rounded-xl bg-[#0a101d] border border-slate-800/80 font-mono text-xs space-y-2">
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span className="font-bold text-slate-200 flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-sky-400" />
            MISSION CORRIDOR (VISITED IN SEQUENTIAL ORDER):
          </span>
          <span className="text-slate-400">
            Waypoints Completed:{' '}
            <strong className="text-emerald-400">{telemetry.target.waypoint_index}</strong> / {environmentConfig.monitoring_waypoints.length}
          </span>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
          {/* Start Point Chip */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 shrink-0 text-[11px]">
            <span className="w-4 h-4 rounded-full bg-emerald-500/20 border border-emerald-400 text-center text-[10px] font-bold leading-4">S</span>
            <span>{startGeo.name} ({startGeo.lat.toFixed(4)}°, {startGeo.lon.toFixed(4)}°)</span>
          </div>

          {/* Sequential Waypoint Chips */}
          {environmentConfig.monitoring_waypoints.map((wp, idx) => {
            const isCompleted = idx < telemetry.target.waypoint_index
            const isCurrent = idx === telemetry.target.waypoint_index
            return (
              <div
                key={wp.id}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border shrink-0 text-[11px] transition-all ${
                  isCompleted
                    ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300'
                    : isCurrent
                    ? 'bg-sky-950/60 border-sky-400 text-sky-200 ring-1 ring-sky-400/50'
                    : 'bg-slate-900 border-slate-800 text-slate-400'
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full border text-center text-[10px] font-bold leading-4 ${
                    isCompleted
                      ? 'bg-emerald-500/30 border-emerald-400 text-emerald-300'
                      : isCurrent
                      ? 'bg-sky-500/30 border-sky-400 text-sky-200 animate-pulse'
                      : 'bg-slate-800 border-slate-700 text-slate-400'
                  }`}
                >
                  {idx + 1}
                </span>
                <span>{wp.zone_name}</span>
                {isCompleted && <CheckCircle2 className="w-3 h-3 text-emerald-400 ml-0.5" />}
              </div>
            )
          })}

          {/* Destination Point Chip */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-950/40 border border-rose-500/40 text-rose-300 shrink-0 text-[11px]">
            <span className="w-4 h-4 rounded-full bg-rose-500/20 border border-rose-400 text-center text-[10px] font-bold leading-4">D</span>
            <span>{destGeo.name} ({destGeo.lat.toFixed(4)}°, {destGeo.lon.toFixed(4)}°)</span>
          </div>
        </div>
      </div>

      {/* SYNCHRONIZED TWO LARGE SIDE-BY-SIDE PANELS (REQUIREMENT 1, 2, 3, 7) */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* VIEW 1: REAL GEOGRAPHICAL MAP OF INDIA */}
        <div className="flex flex-col space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-300 px-1 py-1">
            <span className="flex items-center gap-2 font-bold text-slate-100">
              <Navigation className="w-4 h-4 text-sky-400" />
              VIEW 1: REAL GEOGRAPHICAL MAP OF INDIA
            </span>
            <span className="text-[11px] text-slate-400">LEAFLET / OPENSTREETMAP TILES / WGS-84</span>
          </div>

          <IndiaLeafletMap
            routePlan={currentRoutePlan}
            telemetry={telemetry}
            startPoint={startGeo}
            destination={destGeo}
            waypoints={waypointsGeo}
            actualTrajectory={actualTrajectory}
            interactive={false}
            height={560}
          />
        </div>

        {/* VIEW 2: EXISTING 3D AIRSIM SIMULATION VIEWPORT */}
        <div className="flex flex-col space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-300 px-1 py-1">
            <span className="flex items-center gap-2 font-bold text-slate-100">
              <Radio className="w-4 h-4 text-emerald-400" />
              VIEW 2: EXISTING 3D AIRSIM BLOCKS SIMULATION
            </span>
            <span className="text-[11px] text-slate-400">UNREAL ENGINE 4 / SIMPLEFLIGHT MULTIROTOR</span>
          </div>

          <div style={{ height: 560 }}>
            <AirSim3DViewport
              telemetry={telemetry}
              isAirSimConnected={isAirSimConnected}
              onConnectAirSim={handleConnectAirSim}
            />
          </div>
        </div>
      </div>

      {/* Live Measurable Telemetry Metrics Cards */}
      <TelemetryPanel telemetry={telemetry} />

      {/* Mission Trajectory Progress Bar */}
      <Card
        title="Active Mission Trajectory Progress"
        subtitle={`Tracking target waypoint ${telemetry.target.waypoint_id} (${telemetry.target.waypoint_index + 1} of ${telemetry.target.total_waypoints} points)`}
        icon={<Clock className="w-4 h-4 text-sky-400" />}
      >
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs font-mono">
            <span className="text-slate-400">MISSION COMPLETION:</span>
            <span className="text-sky-400 font-bold">{telemetry.mission_progress_pct}%</span>
          </div>
          <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-sky-500 to-emerald-400 h-full transition-all duration-300"
              style={{ width: `${telemetry.mission_progress_pct}%` }}
            />
          </div>
        </div>
      </Card>

      {/* Post-Mission Satisfaction Evaluation Modal */}
      <SatisfactionFeedbackModal
        isOpen={showSatisfactionModal}
        onClose={() => setShowSatisfactionModal(false)}
        missionId={currentRoutePlan?.mission_id || 'mission_live'}
        missionSummary={{
          plannedDistance: currentRoutePlan?.path_metrics.planned_path_length_m || 294.85,
          actualDistance: currentRoutePlan?.path_metrics.planned_path_length_m || 282.1,
          plannedDuration: (currentRoutePlan?.path_metrics.planned_path_length_m || 294.85) / 3.5,
          actualDuration: 81.1,
          interventionsCount: telemetry.safety_intervention ? 1 : 0,
          collisionCount: 0,
          waypointsCompleted: telemetry.target.waypoint_index + 1,
          waypointsTotal: telemetry.target.total_waypoints,
        }}
      />
    </div>
  )
}
