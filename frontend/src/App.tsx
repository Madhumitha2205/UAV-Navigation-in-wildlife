import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { DashboardLayout } from './components/layout/DashboardLayout'
import { OverviewPage } from './pages/OverviewPage'
import { MissionConfigurationPage } from './pages/MissionConfigurationPage'
import { GlobalPlannerPage } from './pages/GlobalPlannerPage'
import { LiveMonitoringPage } from './pages/LiveMonitoringPage'
import { SafetyMonitoringPage } from './pages/SafetyMonitoringPage'
import { MissionAnalyticsPage } from './pages/MissionAnalyticsPage'
import { ExperimentComparisonPage } from './pages/ExperimentComparisonPage'
import { SettingsPage } from './pages/SettingsPage'

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="mission-config" element={<MissionConfigurationPage />} />
          <Route path="planner" element={<GlobalPlannerPage />} />
          <Route path="monitoring" element={<LiveMonitoringPage />} />
          <Route path="safety" element={<SafetyMonitoringPage />} />
          <Route path="analytics" element={<MissionAnalyticsPage />} />
          <Route path="comparison" element={<ExperimentComparisonPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
