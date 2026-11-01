import React from 'react'
import { FolderSearch } from 'lucide-react'
import { Button } from './Button'

export interface EmptyStateProps {
  title?: string
  description?: string
  actionLabel?: string
  onAction?: () => void
  icon?: React.ReactNode
  height?: string
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Data Available',
  description = 'No telemetry records or mission results found.',
  actionLabel,
  onAction,
  icon,
  height = 'h-64',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center ${height} text-center p-6 border border-dashed border-slate-800 rounded-xl bg-slate-900/20`}
    >
      <div className="p-3 bg-slate-800/60 rounded-full text-slate-400 mb-3 border border-slate-700/50">
        {icon || <FolderSearch className="w-8 h-8" />}
      </div>
      <h4 className="text-base font-medium text-slate-200">{title}</h4>
      <p className="text-sm text-slate-400 max-w-sm mt-1">{description}</p>
      {actionLabel && onAction && (
        <Button variant="secondary" size="sm" onClick={onAction} className="mt-4">
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
