import React from 'react'
import { Loader2 } from 'lucide-react'

export interface LoadingStateProps {
  message?: string
  height?: string
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Processing navigation telemetry...',
  height = 'h-64',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center ${height} text-center p-6 text-slate-400`}>
      <Loader2 className="w-8 h-8 text-sky-400 animate-spin mb-3" />
      <p className="text-sm font-medium text-slate-300">{message}</p>
      <span className="text-xs text-slate-500 mt-1">Acquiring sensor lock...</span>
    </div>
  )
}
