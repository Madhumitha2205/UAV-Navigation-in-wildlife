import React from 'react'
import { ActivityEvent } from '../../types/mission'
import { Card } from '../common/Card'
import { Activity, Radio, Cpu, ShieldAlert, CheckCircle2 } from 'lucide-react'

export interface ActivityFeedProps {
  events: ActivityEvent[]
}

export const ActivityFeed: React.FC<ActivityFeedProps> = ({ events }) => {
  const getIcon = (category: ActivityEvent['category']) => {
    switch (category) {
      case 'PLANNER':
        return <Cpu className="w-3.5 h-3.5 text-purple-400" />
      case 'SIMULATION':
        return <Radio className="w-3.5 h-3.5 text-sky-400" />
      case 'SAFETY':
        return <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
      default:
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
    }
  }

  const getSeverityDot = (severity: ActivityEvent['severity']) => {
    switch (severity) {
      case 'danger':
        return 'bg-rose-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]'
      case 'warning':
        return 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]'
      case 'success':
        return 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]'
      default:
        return 'bg-sky-500 shadow-[0_0_8px_rgba(14,165,233,0.5)]'
    }
  }

  return (
    <Card
      title="Live Mission Activity & System Audit"
      subtitle="Autonomous navigation events, planner jobs, and safety logs"
      icon={<Activity className="w-4 h-4 text-sky-400" />}
    >
      <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
        {events.length === 0 ? (
          <p className="text-xs text-slate-500 text-center py-6">No recent events logged</p>
        ) : (
          events.map((event) => (
            <div
              key={event.id}
              className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-900/50 border border-slate-800/80 hover:bg-slate-900/80 transition-colors"
            >
              <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${getSeverityDot(event.severity)}`} />

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getIcon(event.category)}
                    <span className="text-xs font-semibold text-slate-200">{event.title}</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">{event.timestamp}</span>
                </div>
                <p className="text-[11px] text-slate-300 mt-1 leading-snug">{event.description}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  )
}
