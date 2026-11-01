import React from 'react'
import { cn } from '../../utils/cn'

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'primary' | 'safe' | 'warning' | 'danger' | 'demo' | 'outline'
  pulse?: boolean
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  className,
  variant = 'default',
  pulse = false,
  ...props
}) => {
  const variantStyles = {
    default: 'bg-slate-800 text-slate-300 border-slate-700',
    primary: 'bg-sky-950/80 text-sky-400 border-sky-800/80 shadow-[0_0_8px_rgba(14,165,233,0.2)]',
    safe: 'bg-emerald-950/80 text-emerald-400 border-emerald-800/80 shadow-[0_0_8px_rgba(16,185,129,0.2)]',
    warning: 'bg-amber-950/80 text-amber-400 border-amber-800/80 shadow-[0_0_8px_rgba(245,158,11,0.2)]',
    danger: 'bg-rose-950/80 text-rose-400 border-rose-800/80 shadow-[0_0_8px_rgba(239,68,68,0.2)]',
    demo: 'bg-purple-950/80 text-purple-300 border-purple-700/80 font-mono tracking-wider shadow-[0_0_8px_rgba(168,85,247,0.25)]',
    outline: 'bg-transparent text-slate-400 border-slate-700',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border transition-colors',
        variantStyles[variant],
        pulse && 'animate-pulse',
        className
      )}
      {...props}
    >
      {pulse && (
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full',
            variant === 'safe' && 'bg-emerald-400',
            variant === 'warning' && 'bg-amber-400',
            variant === 'danger' && 'bg-rose-400',
            variant === 'primary' && 'bg-sky-400',
            variant === 'demo' && 'bg-purple-400'
          )}
        />
      )}
      {children}
    </span>
  )
}
