import React from 'react'
import { Card } from '../common/Card'

export const RouteLegend: React.FC = () => {
  return (
    <Card title="Map Legend & Symbology" className="p-0">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
        {/* Start */}
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full bg-emerald-500 border border-white flex items-center justify-center text-[8px] font-bold text-white">
            S
          </span>
          <span className="text-slate-300">Start (0,0)</span>
        </div>

        {/* Destination */}
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full bg-rose-500 border border-white flex items-center justify-center text-[8px] font-bold text-white">
            D
          </span>
          <span className="text-slate-300">Destination</span>
        </div>

        {/* Monitoring Waypoint */}
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full bg-cyan-400 border border-cyan-200" />
          <span className="text-slate-300">Monitoring WP</span>
        </div>

        {/* Optimized Route */}
        <div className="flex items-center gap-2">
          <span className="w-5 h-1 bg-sky-400 rounded-full" />
          <span className="text-slate-300">GA + 2-Opt Route</span>
        </div>

        {/* Obstacle */}
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded bg-rose-900 border border-rose-500" />
          <span className="text-slate-300">Static Obstacle</span>
        </div>

        {/* Safety Buffer */}
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full border border-dashed border-amber-400 bg-amber-500/10" />
          <span className="text-slate-300">Safety Clearance</span>
        </div>
      </div>
    </Card>
  )
}
