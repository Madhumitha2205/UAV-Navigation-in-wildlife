import React from 'react'
import { AlertCircle, RotateCcw } from 'lucide-react'
import { Button } from './Button'

export interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
  height?: string
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Telemetry & Navigation Error',
  message,
  onRetry,
  height = 'h-64',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center ${height} text-center p-6 bg-rose-950/20 border border-rose-900/40 rounded-xl m-2`}
    >
      <div className="p-3 bg-rose-900/30 rounded-full text-rose-400 mb-3 border border-rose-800/50">
        <AlertCircle className="w-8 h-8" />
      </div>
      <h4 className="text-base font-semibold text-rose-200">{title}</h4>
      <p className="text-sm text-slate-300 max-w-md mt-1.5 leading-relaxed">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-4 gap-2">
          <RotateCcw className="w-4 h-4" />
          Retry Connection
        </Button>
      )}
    </div>
  )
}
