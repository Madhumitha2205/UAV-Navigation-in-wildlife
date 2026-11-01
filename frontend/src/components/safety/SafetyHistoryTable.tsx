import React from 'react'
import { Card } from '../common/Card'
import { Badge } from '../common/Badge'
import { SafetyEvent } from '../../types/safety'
import { formatDistance } from '../../utils/formatters'
import { History } from 'lucide-react'

export interface SafetyHistoryTableProps {
  events: SafetyEvent[]
}

export const SafetyHistoryTable: React.FC<SafetyHistoryTableProps> = ({ events }) => {
  return (
    <Card
      title="Adaptive Fuzzy Safety Intervention Audit Log"
      subtitle="Chronological record of obstacle encounters and velocity adjustment reasons"
      icon={<History className="w-4 h-4 text-purple-400" />}
    >
      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-xs text-left">
          <thead className="bg-slate-900/80 text-slate-400 font-mono border-b border-slate-800">
            <tr>
              <th className="py-2.5 px-3">Time</th>
              <th className="py-2.5 px-3">Hazard</th>
              <th className="py-2.5 px-3">Distance</th>
              <th className="py-2.5 px-3">Danger</th>
              <th className="py-2.5 px-3">TD3 Command</th>
              <th className="py-2.5 px-3">Applied Command</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3">Intervention Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {events.map((evt) => (
              <tr key={evt.id} className="hover:bg-slate-800/30 transition-colors">
                <td className="py-2.5 px-3 text-slate-400">{evt.timestamp}</td>
                <td className="py-2.5 px-3 text-rose-300 font-semibold">
                  {evt.closest_obstacle_id || 'OBS_GEN'}
                </td>
                <td className="py-2.5 px-3 text-slate-200">
                  {formatDistance(evt.obstacle_distance_m)}
                </td>
                <td className="py-2.5 px-3">
                  <Badge
                    variant={evt.danger_level === 'SAFE' ? 'safe' : evt.danger_level === 'WARNING' ? 'warning' : 'danger'}
                    className="text-[10px]"
                  >
                    {evt.danger_level}
                  </Badge>
                </td>
                <td className="py-2.5 px-3 text-slate-400">
                  [{evt.td3_velocity.join(', ')}]
                </td>
                <td className="py-2.5 px-3 text-emerald-400 font-bold">
                  [{evt.final_velocity.join(', ')}]
                </td>
                <td className="py-2.5 px-3">
                  <span className={evt.intervention_status ? 'text-amber-400 font-bold' : 'text-slate-500'}>
                    {evt.intervention_status ? 'ADJUSTED' : 'NOMINAL'}
                  </span>
                </td>
                <td className="py-2.5 px-3 font-sans text-slate-300 max-w-xs truncate" title={evt.intervention_reason}>
                  {evt.intervention_reason}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
