import React from 'react'
import { Card } from '../common/Card'
import { EnvironmentConfig } from '../../types/environment'
import { Map, Navigation } from 'lucide-react'

export interface EnvironmentFormProps {
  config: EnvironmentConfig
  onChange: (updated: Partial<EnvironmentConfig>) => void
}

export const EnvironmentForm: React.FC<EnvironmentFormProps> = ({ config, onChange }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Simulation Bounds & Resolution */}
      <Card
        title="Environment Bounds & Safety Clearance"
        subtitle="Global survey zone dimensions and hazard buffering"
        icon={<Map className="w-4 h-4 text-sky-400" />}
      >
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div>
            <label className="block text-slate-400 mb-1">Width (East, m)</label>
            <input
              type="number"
              value={config.width}
              onChange={(e) => onChange({ width: parseFloat(e.target.value) || 0 })}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-slate-400 mb-1">Height (North, m)</label>
            <input
              type="number"
              value={config.height}
              onChange={(e) => onChange({ height: parseFloat(e.target.value) || 0 })}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-slate-400 mb-1">Grid Resolution (m)</label>
            <input
              type="number"
              step="0.5"
              value={config.grid_resolution}
              onChange={(e) => onChange({ grid_resolution: parseFloat(e.target.value) || 1 })}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-slate-400 mb-1">Safety Clearance (m)</label>
            <input
              type="number"
              step="0.5"
              value={config.safety_clearance_m}
              onChange={(e) => onChange({ safety_clearance_m: parseFloat(e.target.value) || 0 })}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
            />
          </div>
        </div>
      </Card>

      {/* Start and Destination 3D Coordinates */}
      <Card
        title="Mission Start & Destination (ENU_ALT_UP)"
        subtitle="Initial takeoff point and final survey recovery destination"
        icon={<Navigation className="w-4 h-4 text-emerald-400" />}
      >
        <div className="space-y-4 text-xs">
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-emerald-400 font-semibold font-mono">UAV START POSITION</span>
              <span className="text-[10px] text-slate-500">X(East), Y(North), Z(Alt Up)</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <input
                type="number"
                placeholder="X"
                value={config.start_position.x}
                onChange={(e) =>
                  onChange({
                    start_position: { ...config.start_position, x: parseFloat(e.target.value) || 0 },
                  })
                }
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono text-center focus:border-emerald-500 focus:outline-none"
              />
              <input
                type="number"
                placeholder="Y"
                value={config.start_position.y}
                onChange={(e) =>
                  onChange({
                    start_position: { ...config.start_position, y: parseFloat(e.target.value) || 0 },
                  })
                }
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono text-center focus:border-emerald-500 focus:outline-none"
              />
              <input
                type="number"
                placeholder="Z"
                value={config.start_position.z}
                onChange={(e) =>
                  onChange({
                    start_position: { ...config.start_position, z: parseFloat(e.target.value) || 0 },
                  })
                }
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono text-center focus:border-emerald-500 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-rose-400 font-semibold font-mono">RECOVERY DESTINATION</span>
              <span className="text-[10px] text-slate-500">X(East), Y(North), Z(Alt Up)</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <input
                type="number"
                placeholder="X"
                value={config.destination.x}
                onChange={(e) =>
                  onChange({
                    destination: { ...config.destination, x: parseFloat(e.target.value) || 0 },
                  })
                }
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono text-center focus:border-rose-500 focus:outline-none"
              />
              <input
                type="number"
                placeholder="Y"
                value={config.destination.y}
                onChange={(e) =>
                  onChange({
                    destination: { ...config.destination, y: parseFloat(e.target.value) || 0 },
                  })
                }
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono text-center focus:border-rose-500 focus:outline-none"
              />
              <input
                type="number"
                placeholder="Z"
                value={config.destination.z}
                onChange={(e) =>
                  onChange({
                    destination: { ...config.destination, z: parseFloat(e.target.value) || 0 },
                  })
                }
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono text-center focus:border-rose-500 focus:outline-none"
              />
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}
