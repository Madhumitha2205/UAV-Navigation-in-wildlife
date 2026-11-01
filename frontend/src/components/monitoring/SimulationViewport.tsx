import React, { useState } from 'react'
import { Video, Eye, Radio, AlertCircle } from 'lucide-react'
import { TelemetryPacket } from '../../types/telemetry'
import { GlobalRoutePlan } from '../../types/route'
import { EnvironmentMap } from '../planner/EnvironmentMap'
import { Badge } from '../common/Badge'

export interface SimulationViewportProps {
  telemetry: TelemetryPacket
  routePlan?: GlobalRoutePlan | null
}

export const SimulationViewport: React.FC<SimulationViewportProps> = ({
  telemetry,
  routePlan,
}) => {
  const [activeTab, setActiveTab] = useState<'MAP' | 'CAMERA'>('MAP')

  return (
    <div className="bg-[#0b1322] border border-slate-800 rounded-xl overflow-hidden relative shadow-xl">
      {/* Viewport Top Control Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900/90 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Radio className="w-4 h-4 text-sky-400 animate-pulse" />
          <span className="text-xs font-mono font-semibold text-slate-200">
            AIRSIM SIMULATION VIEWPORT
          </span>
          <Badge variant="primary" className="text-[10px]">
            {telemetry.flight_state}
          </Badge>
        </div>

        {/* View Switcher */}
        <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
          <button
            onClick={() => setActiveTab('MAP')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded font-mono transition-colors ${
              activeTab === 'MAP'
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Eye className="w-3.5 h-3.5" />
            2D Telemetry Radar
          </button>
          <button
            onClick={() => setActiveTab('CAMERA')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded font-mono transition-colors ${
              activeTab === 'CAMERA'
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Video className="w-3.5 h-3.5" />
            AirSim Camera Feed
          </button>
        </div>
      </div>

      {/* Main Viewport Content Area */}
      <div className="relative min-h-[480px] bg-[#070b14] flex flex-col items-center justify-center">
        {activeTab === 'MAP' ? (
          <div className="w-full h-full">
            <EnvironmentMap
              routePlan={routePlan}
              uavPosition={telemetry.position}
              height={480}
            />
          </div>
        ) : (
          /* AirSim Camera Stream Area - Explicitly truthful when no camera server is connected */
          <div className="flex flex-col items-center justify-center text-center p-8 max-w-md">
            <div className="p-4 bg-slate-900/80 rounded-full text-slate-500 border border-slate-800 mb-3">
              <Video className="w-10 h-10 text-slate-400" />
            </div>
            <h4 className="text-sm font-semibold text-slate-200">
              AirSim Video Stream Standby
            </h4>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              AirSim multirotor camera feed is currently not streaming. The interface displays
              high-frequency 2D trajectory & safety telemetry until the WebRTC or RTSP camera
              proxy is started on the simulation host.
            </p>
            <div className="mt-4 flex items-center gap-2 text-[11px] font-mono text-amber-400 bg-amber-950/40 px-3 py-1.5 rounded-md border border-amber-800/60">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>Camera RPC Endpoint: Pending AirSim Part 2 Link</span>
            </div>
          </div>
        )}

        {/* HUD Telemetry Overlay on Bottom of Viewport */}
        <div className="absolute bottom-3 right-3 z-10 bg-slate-950/80 border border-slate-800 rounded-lg p-2.5 text-[11px] font-mono text-slate-300 backdrop-blur-md space-y-1">
          <div className="flex justify-between gap-4">
            <span className="text-slate-500">SPD:</span>
            <span className="text-emerald-400 font-bold">{telemetry.velocity.speed} m/s</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-slate-500">ALT:</span>
            <span className="text-cyan-400 font-bold">{telemetry.position.z} m</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-slate-500">PROGRESS:</span>
            <span className="text-sky-300 font-bold">{telemetry.mission_progress_pct}%</span>
          </div>
        </div>
      </div>
    </div>
  )
}
