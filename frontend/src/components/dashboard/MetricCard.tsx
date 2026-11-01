import React from 'react'
import { Card } from '../common/Card'
import { cn } from '../../utils/cn'

export interface MetricCardProps {
  title: string
  value: React.ReactNode
  unit?: string
  sublabel?: string
  icon?: React.ReactNode
  variant?: 'default' | 'safe' | 'warning' | 'danger' | 'primary'
  badge?: React.ReactNode
  className?: string
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  sublabel,
  icon,
  variant = 'default',
  badge,
  className,
}) => {
  const valueColor = {
    default: 'text-slate-100',
    safe: 'text-emerald-400',
    warning: 'text-amber-400',
    danger: 'text-rose-400',
    primary: 'text-sky-400',
  }

  return (
    <Card className={cn('p-4 bg-[#0c1424] border-slate-800/90 relative overflow-hidden', className)}>
      <div className="flex items-center justify-between text-slate-400 mb-2">
        <span className="text-xs font-mono tracking-wider uppercase font-medium">{title}</span>
        {icon && <div className="text-slate-400">{icon}</div>}
      </div>

      <div className="flex items-baseline gap-1.5">
        <div className={cn('text-2xl font-bold font-mono tracking-tight', valueColor[variant])}>
          {value}
        </div>
        {unit && <span className="text-xs text-slate-400 font-mono font-normal">{unit}</span>}
      </div>

      <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-800/60">
        <span className="text-[11px] text-slate-400 truncate">{sublabel || 'Telemetry status'}</span>
        {badge}
      </div>
    </Card>
  )
}
