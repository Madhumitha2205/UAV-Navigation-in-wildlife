import React from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { useTelemetry } from '../../hooks/useTelemetry'

export const DashboardLayout: React.FC = () => {
  // Activate telemetry subscription lifecycle for the application
  useTelemetry()

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#090d16] text-slate-100 font-sans">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6 bg-[#090d16] hud-grid">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
