import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Sliders,
  Route,
  Navigation,
  ShieldAlert,
  BarChart3,
  GitCompare,
  Settings,
  Compass,
} from 'lucide-react'
import { Badge } from '../common/Badge'
import { useSettingsStore } from '../../store/settingsStore'

const navItems = [
  { name: 'Overview', path: '/', icon: LayoutDashboard },
  { name: 'Mission Configuration', path: '/mission-config', icon: Sliders },
  { name: 'Global Route Planner', path: '/planner', icon: Route },
  { name: 'Live UAV Monitoring', path: '/monitoring', icon: Navigation },
  { name: 'Safety & Obstacles', path: '/safety', icon: ShieldAlert },
  { name: 'Mission Analytics', path: '/analytics', icon: BarChart3 },
  { name: 'Experiment Comparison', path: '/comparison', icon: GitCompare },
  { name: 'Settings', path: '/settings', icon: Settings },
]

export const Sidebar: React.FC = () => {
  const { demoMode } = useSettingsStore()

  return (
    <aside className="w-64 bg-[#0a0f1d] border-r border-slate-800/90 flex flex-col shrink-0 min-h-screen select-none">
      {/* Brand Header */}
      <div className="px-5 py-5 border-b border-slate-800/80 flex items-center gap-3 bg-[#0d1424]">
        <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 shadow-[0_0_12px_rgba(14,165,233,0.25)]">
          <Compass className="w-5 h-5 animate-[spin_12s_linear_infinite]" />
        </div>
        <div>
          <h1 className="text-xs font-bold tracking-wider text-slate-100 uppercase">
            Wildlife UAV
          </h1>
          <p className="text-[10px] text-sky-400 font-mono tracking-tight font-medium">
            HIERARCHICAL NAV
          </p>
        </div>
      </div>

      {/* Mode Tag */}
      <div className="px-5 py-3 border-b border-slate-800/60 bg-slate-900/40 flex items-center justify-between">
        <span className="text-[11px] font-mono text-slate-400">OPERATION MODE</span>
        {demoMode ? (
          <Badge variant="demo" pulse>
            SIM DEMO
          </Badge>
        ) : (
          <Badge variant="safe" pulse>
            LIVE BACKEND
          </Badge>
        )}
      </div>

      {/* Navigation List */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all group ${
                  isActive
                    ? 'bg-sky-600/15 text-sky-300 border border-sky-500/40 shadow-[0_0_10px_rgba(14,165,233,0.15)] font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive ? 'text-sky-400' : 'text-slate-400 group-hover:text-slate-300'
                    }`}
                  />
                  <span>{item.name}</span>
                </>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* System Framework Footprint */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/60 text-[11px] font-mono text-slate-500 space-y-1">
        <div className="flex justify-between">
          <span>GLOBAL:</span>
          <span className="text-slate-400">GA + 2-Opt + A*</span>
        </div>
        <div className="flex justify-between">
          <span>LOCAL RL:</span>
          <span className="text-slate-400">TD3 Policy</span>
        </div>
        <div className="flex justify-between">
          <span>SAFETY:</span>
          <span className="text-slate-400">Adaptive Fuzzy</span>
        </div>
      </div>
    </aside>
  )
}
