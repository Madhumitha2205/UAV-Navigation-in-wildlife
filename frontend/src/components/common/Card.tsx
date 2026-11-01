import React from 'react'
import { cn } from '../../utils/cn'

export interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: React.ReactNode
  subtitle?: React.ReactNode
  action?: React.ReactNode
  icon?: React.ReactNode
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  title,
  subtitle,
  action,
  icon,
  ...props
}) => {
  return (
    <div
      className={cn(
        'bg-[#0d1527] border border-slate-800/90 rounded-xl shadow-lg relative overflow-hidden backdrop-blur-sm',
        className
      )}
      {...props}
    >
      {(title || action) && (
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800/70 bg-slate-900/40">
          <div className="flex items-center gap-3">
            {icon && <div className="text-sky-400">{icon}</div>}
            <div>
              {title && <h3 className="text-sm font-semibold text-slate-100 tracking-wide">{title}</h3>}
              {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
            </div>
          </div>
          {action && <div className="flex items-center gap-2">{action}</div>}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  )
}
