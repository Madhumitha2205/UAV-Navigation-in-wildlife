import React, { useState } from 'react'
import {
  Compass,
  Radio,
  Eye,
  Camera,
  AlertCircle,
  CheckCircle2,
  Activity,
  Layers,
  Gauge,
  Sliders,
  Crosshair,
} from 'lucide-react'
import { TelemetryPacket } from '../../types/telemetry'
import { Badge } from '../common/Badge'

export interface AirSim3DViewportProps {
  telemetry: TelemetryPacket
  onConnectAirSim?: () => void
  isAirSimConnected: boolean
}

export const AirSim3DViewport: React.FC<AirSim3DViewportProps> = ({
  telemetry,
  onConnectAirSim,
  isAirSimConnected,
}) => {
  const [cameraAngle, setCameraAngle] = useState<'FPV' | 'CHASE' | 'TOP_DOWN'>('FPV')

  // Calculate synthetic attitude from velocity and heading for HUD rendering
  const vx = telemetry.velocity.vx
  const vy = telemetry.velocity.vy
  const vz = telemetry.velocity.vz
  const speed = telemetry.velocity.speed
  const pitchDeg = Math.max(-25, Math.min(25, -vz * 4.0))
  const rollDeg = Math.max(-30, Math.min(30, (vx * 0.7 - vy * 0.3) * 3.5))
  const headingDeg = telemetry.closest_obstacle_bearing_deg || 0

  return (
    <div className="flex flex-col h-full bg-[#070b14] border border-slate-800 rounded-xl overflow-hidden shadow-2xl relative">
      {/* Viewport Top Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900/90 border-b border-slate-800 text-xs">
        <div className="flex items-center gap-2">
          <Radio className={`w-4 h-4 ${isAirSimConnected ? 'text-emerald-400 animate-pulse' : 'text-amber-400'}`} />
          <span className="font-mono font-bold text-slate-100 tracking-wider">
            3D AIRSIM SIMULATION VIEWPORT
          </span>
          <Badge variant={isAirSimConnected ? 'safe' : 'danger'} className="text-[10px]">
            {isAirSimConnected ? 'AIRSIM 3D CONNECTED (127.0.0.1:41451)' : 'AIRSIM DISCONNECTED'}
          </Badge>
        </div>

        {/* Camera Perspective Selector */}
        <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 font-mono text-[11px]">
          {(['FPV', 'CHASE', 'TOP_DOWN'] as const).map((cam) => (
            <button
              key={cam}
              onClick={() => setCameraAngle(cam)}
              className={`px-2 py-0.5 rounded transition-colors ${
                cameraAngle === cam
                  ? 'bg-sky-600 text-white font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {cam}
            </button>
          ))}
        </div>
      </div>

      {/* Main 3D Virtual Cockpit / AirSim HUD Area */}
      <div className="relative flex-1 min-h-[420px] bg-gradient-to-b from-[#060c18] via-[#091426] to-[#040810] flex items-center justify-center overflow-hidden p-6 select-none">
        {/* Background 3D Grid Perspective */}
        <div
          className="absolute inset-0 opacity-20 pointer-events-none"
          style={{
            backgroundImage:
              'linear-gradient(to right, #0284c7 1px, transparent 1px), linear-gradient(to bottom, #0284c7 1px, transparent 1px)',
            backgroundSize: '40px 40px',
            transform: 'perspective(500px) rotateX(60deg) translateY(40px)',
          }}
        />

        {/* AirSim Unreal Connection Status & Instruction Overlay */}
        <div className="absolute top-4 left-4 z-10 pointer-events-none">
          <div className="p-3 rounded-lg bg-slate-900/85 border border-slate-800 backdrop-blur-md font-mono text-[11px] space-y-1 shadow-lg max-w-xs">
            <div className="flex items-center gap-1.5 text-sky-400 font-bold">
              <Activity className="w-3.5 h-3.5" />
              AIRSIM VEHICLE STATE
            </div>
            <div className="text-slate-300">
              Model: <span className="text-slate-100 font-semibold">SimpleFlight Multirotor</span>
            </div>
            <div className="text-slate-300">
              Sensor: <span className="text-slate-100 font-semibold">LidarSensor1 (360° Raycast)</span>
            </div>
            <div className="text-slate-300">
              Position NED:{' '}
              <span className="text-sky-300">
                N:{telemetry.position.y.toFixed(1)} E:{telemetry.position.x.toFixed(1)} D:{-telemetry.position.z.toFixed(1)}
              </span>
            </div>
            <div className="text-slate-300">
              Control: <span className="text-emerald-400 font-semibold">TD3 + Adaptive Fuzzy Safety</span>
            </div>
          </div>
        </div>

        {/* Primary Flight Display HUD (Attitude Indicator & Crosshairs) */}
        <div className="relative w-64 h-64 rounded-full border border-sky-500/20 flex items-center justify-center pointer-events-none">
          {/* Pitch & Roll Horizon Line */}
          <div
            className="absolute w-48 h-0.5 bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.8)] transition-transform duration-150"
            style={{
              transform: `rotate(${rollDeg}deg) translateY(${pitchDeg * 2}px)`,
            }}
          >
            {/* Horizon ticks */}
            <div className="absolute left-0 -top-2 w-0.5 h-2 bg-emerald-400" />
            <div className="absolute right-0 -top-2 w-0.5 h-2 bg-emerald-400" />
          </div>

          {/* Central Fixed Aircraft Crosshair */}
          <div className="relative flex items-center justify-center z-10 text-amber-400">
            <div className="w-6 h-0.5 bg-amber-400" />
            <div className="w-3 h-3 rounded-full border border-amber-400 mx-1" />
            <div className="w-6 h-0.5 bg-amber-400" />
          </div>

          {/* Compass Ring */}
          <div className="absolute inset-0 rounded-full border-2 border-dashed border-sky-500/30 animate-[spin_60s_linear_infinite]" />
          <div className="absolute top-2 font-mono text-[10px] text-sky-400 font-bold">N</div>
          <div className="absolute bottom-2 font-mono text-[10px] text-slate-500">S</div>
          <div className="absolute right-2 font-mono text-[10px] text-slate-500">E</div>
          <div className="absolute left-2 font-mono text-[10px] text-slate-500">W</div>
        </div>

        {/* Airspeed Ladder (Left) */}
        <div className="absolute left-6 top-1/2 -translate-y-1/2 p-2 bg-slate-900/80 border border-slate-800 rounded font-mono text-[11px] text-center w-16 shadow-lg backdrop-blur-sm pointer-events-none">
          <div className="text-[9px] text-slate-500">AIRSPEED</div>
          <div className="text-base font-bold text-sky-400">{speed.toFixed(1)}</div>
          <div className="text-[9px] text-slate-500">M/S</div>
        </div>

        {/* Altitude Ladder (Right) */}
        <div className="absolute right-6 top-1/2 -translate-y-1/2 p-2 bg-slate-900/80 border border-slate-800 rounded font-mono text-[11px] text-center w-16 shadow-lg backdrop-blur-sm pointer-events-none">
          <div className="text-[9px] text-slate-500">ALTITUDE</div>
          <div className="text-base font-bold text-emerald-400">{telemetry.position.z.toFixed(1)}</div>
          <div className="text-[9px] text-slate-500">METRES</div>
        </div>

        {/* Bottom Banner Alert if AirSim is not connected */}
        {!isAirSimConnected && (
          <div className="absolute bottom-4 inset-x-6 z-10">
            <div className="p-2.5 rounded-lg bg-rose-950/80 border border-rose-500/50 backdrop-blur-md flex items-center justify-between text-xs text-slate-200">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>
                  <strong className="text-rose-300">AirSim Simulator Disconnected:</strong> Start the configured AirSim Blocks simulator and connect before starting a live 3D mission.
                </span>
              </div>
              {onConnectAirSim && (
                <button
                  onClick={onConnectAirSim}
                  className="px-2.5 py-1 rounded bg-sky-600 hover:bg-sky-500 text-white font-mono text-[11px] font-semibold transition-colors shrink-0 ml-3"
                >
                  Connect AirSim
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Viewport Bottom Flight Telemetry Bar */}
      <div className="px-4 py-2.5 bg-slate-900/90 border-t border-slate-800 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
        <div>
          <span className="text-slate-500 block text-[10px]">FLIGHT STATE</span>
          <span className="text-sky-300 font-semibold">{telemetry.flight_state}</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px]">ACTIVE WAYPOINT</span>
          <span className="text-slate-200 font-semibold">
            {telemetry.target.waypoint_id} ({telemetry.target.waypoint_index + 1}/{telemetry.target.total_waypoints})
          </span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px]">DISTANCE TO TARGET</span>
          <span className="text-slate-200 font-semibold">{telemetry.target.distance_to_target_m.toFixed(1)} m</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px]">CLOSEST OBSTACLE</span>
          <span className={`font-semibold ${telemetry.closest_obstacle_distance_m < 6.0 ? 'text-rose-400' : 'text-emerald-400'}`}>
            {telemetry.closest_obstacle_distance_m.toFixed(1)} m
          </span>
        </div>
      </div>
    </div>
  )
}
