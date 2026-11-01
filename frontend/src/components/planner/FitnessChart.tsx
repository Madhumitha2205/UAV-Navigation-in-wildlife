import React from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { FitnessGenerationRecord } from '../../types/route'
import { Card } from '../common/Card'
import { TrendingDown } from 'lucide-react'

export interface FitnessChartProps {
  data?: FitnessGenerationRecord[]
}

export const FitnessChart: React.FC<FitnessChartProps> = ({ data = [] }) => {
  return (
    <Card
      title="GA Optimization Fitness History"
      subtitle="Evolutionary cost minimization across generations (Path Length & Penalties)"
      icon={<TrendingDown className="w-4 h-4 text-sky-400" />}
    >
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey="generation"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              unit=" gen"
            />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              domain={['auto', 'auto']}
              unit="m"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f172a',
                borderColor: '#334155',
                borderRadius: '8px',
                fontSize: '12px',
                color: '#f8fafc',
              }}
              formatter={(value: any) => [`${Number(value).toFixed(2)} m`, 'Cost / Length']}
              labelFormatter={(label) => `Generation: ${label}`}
            />
            <Legend
              verticalAlign="top"
              align="right"
              wrapperStyle={{ fontSize: '11px', paddingBottom: '10px' }}
            />
            <Line
              type="monotone"
              dataKey="best_fitness"
              name="Best Individual Fitness"
              stroke="#0ea5e9"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5, fill: '#38bdf8' }}
            />
            {data.some((d) => d.avg_fitness !== undefined) && (
              <Line
                type="monotone"
                dataKey="avg_fitness"
                name="Population Average"
                stroke="#64748b"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}
