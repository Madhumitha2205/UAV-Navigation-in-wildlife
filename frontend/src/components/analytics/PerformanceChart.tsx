import React from 'react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Card } from '../common/Card'
import { MissionAnalyticsSummary } from '../../types/analytics'
import { BarChart3, TrendingUp } from 'lucide-react'

export interface PerformanceChartProps {
  summary: MissionAnalyticsSummary
}

export const PerformanceChart: React.FC<PerformanceChartProps> = ({ summary }) => {
  // Distance comparison data
  const distanceData = [
    {
      category: 'Route Distance (m)',
      Planned: summary.planned_route_length_m,
      Actual: summary.actual_travelled_distance_m,
    },
  ]

  // Mock telemetry speed & altitude profile over execution time
  const profileData = Array.from({ length: 15 }, (_, i) => {
    const sec = i * 3
    const speed = 2.2 + Math.sin(i * 0.5) * 0.6
    const alt = 15.0 + Math.sin(i * 0.4) * 2.2
    return {
      time: `${sec}s`,
      speed: Number(speed.toFixed(2)),
      altitude: Number(alt.toFixed(1)),
    }
  })

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Planned vs Actual Distance */}
      <Card
        title="Planned vs Actual Flown Trajectory Distance"
        subtitle="GA + 2-Opt theoretical route length vs TD3 + AFL simulation path"
        icon={<BarChart3 className="w-4 h-4 text-sky-400" />}
      >
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={distanceData} margin={{ top: 20, right: 30, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="category" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} unit="m" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '8px',
                  color: '#f8fafc',
                }}
              />
              <Legend verticalAlign="top" align="right" wrapperStyle={{ fontSize: '11px' }} />
              <Bar dataKey="Planned" fill="#0ea5e9" name="Planned GA Route (m)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Actual" fill="#10b981" name="Actual Flown Trajectory (m)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Speed & Altitude Flight Profile */}
      <Card
        title="Kinematic Flight Profile Over Time"
        subtitle="Real-time multirotor velocity and altitude tracking"
        icon={<TrendingUp className="w-4 h-4 text-emerald-400" />}
      >
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={profileData} margin={{ top: 20, right: 30, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
              <YAxis yAxisId="left" stroke="#10b981" fontSize={11} unit=" m/s" />
              <YAxis yAxisId="right" orientation="right" stroke="#0ea5e9" fontSize={11} unit=" m" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '8px',
                  color: '#f8fafc',
                }}
              />
              <Legend verticalAlign="top" align="right" wrapperStyle={{ fontSize: '11px' }} />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="speed"
                name="Speed (m/s)"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="altitude"
                name="Altitude (m)"
                stroke="#0ea5e9"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  )
}
