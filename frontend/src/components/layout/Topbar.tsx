import React, { useState, useEffect } from 'react'
import { Activity, Radio, Cpu, Bell, ToggleLeft, ToggleRight } from 'lucide-react'
import { Badge } from '../common/Badge'
import { useSettingsStore } from '../../store/settingsStore'
import { useConnectionStatus } from '../../hooks/useConnectionStatus'

export const Topbar: React.FC = () => {
  const { demoMode, setDemoMode } = useSettingsStore()
  const connection = useConnectionStatus()
  const [clock, setClock] = useState<string>('')

  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      setClock(now.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    }
    updateTime()
    const timer = setInterval(updateTime, 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <header className="h-16 bg-[#0c1322] border-b border-slate-800/80 px-6 flex items-center justify-between shrink-0 select-none z-10">
      {/* Title */}
      <div className="flex items-center gap-3">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-slate-100 uppercase">
            WILDLIFE UAV — Intelligent Navigation and Monitoring System
          </h2>
          <p className="text-[11px] text-slate-400">
            Hierarchical Autonomous Multi-Sensor Mission Dashboard
          </p>
        </div>
      </div>

      {/* Status Badges & Controls */}
      <div className="flex items-center gap-4">
        {/* Planner API status */}
        <div className="hidden lg:flex items-center gap-1.5 text-xs text-slate-400 font-mono">
          <Cpu className="w-3.5 h-3.5 text-sky-400" />
          <span>PLANNER:</span>
          <Badge
            variant={connection.global_planner_api === 'ONLINE' ? 'safe' : 'danger'}
            className="text-[10px] py-0 px-2"
          >
            {connection.global_planner_api}
          </Badge>
        </div>

        {/* AirSim / Control API status */}
        <div className="hidden lg:flex items-center gap-1.5 text-xs text-slate-400 font-mono">
          <Activity className="w-3.5 h-3.5 text-sky-400" />
          <span>AIRSIM:</span>
          <Badge
            variant={connection.airsim_simulation === 'CONNECTED' ? 'safe' : 'warning'}
            className="text-[10px] py-0 px-2"
          >
            {connection.airsim_simulation}
          </Badge>
        </div>

        {/* Telemetry WS status */}
        <div className="hidden sm:flex items-center gap-1.5 text-xs text-slate-400 font-mono">
          <Radio className="w-3.5 h-3.5 text-sky-400" />
          <span>TELEMETRY:</span>
          <Badge
            variant={connection.websocket_telemetry === 'CONNECTED' ? 'safe' : 'warning'}
            className="text-[10px] py-0 px-2"
            pulse={connection.websocket_telemetry === 'CONNECTED'}
          >
            {connection.websocket_telemetry}
          </Badge>
        </div>

        {/* Mode Switch Button */}
        <button
          onClick={() => setDemoMode(!demoMode)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono transition-all ${
            demoMode
              ? 'bg-purple-950/60 border-purple-700/80 text-purple-200 hover:bg-purple-900/60'
              : 'bg-emerald-950/60 border-emerald-700/80 text-emerald-200 hover:bg-emerald-900/60'
          }`}
          title="Toggle between Simulated Demo Mode and Live Backend Connection"
        >
          {demoMode ? (
            <>
              <ToggleLeft className="w-4 h-4 text-purple-400" />
              <span>DEMO MODE</span>
            </>
          ) : (
            <>
              <ToggleRight className="w-4 h-4 text-emerald-400" />
              <span>LIVE MODE</span>
            </>
          )}
        </button>

        {/* Clock */}
        <div className="px-2.5 py-1 bg-slate-900/80 border border-slate-800 rounded font-mono text-xs text-sky-300">
          {clock || '00:00:00'}
        </div>

        {/* Notification Icon */}
        <div className="relative text-slate-400 hover:text-slate-200 cursor-pointer p-1">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-sky-400" />
        </div>
      </div>
    </header>
  )
}
