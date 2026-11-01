import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { App } from '../App'

// Mock resize observer for Recharts in tests
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserver

describe('Application Routing and Sidebar Navigation', () => {
  it('renders Overview page on default root route', () => {
    render(<App />)
    expect(screen.getByText('AUTONOMOUS MISSION CONTROL CENTER')).toBeInTheDocument()
    expect(screen.getAllByText(/WILDLIFE UAV/i).length).toBeGreaterThan(0)
  })

  it('navigates to Mission Configuration page via sidebar', () => {
    render(<App />)
    const missionConfigLink = screen.getByRole('link', { name: /Mission Configuration/i })
    fireEvent.click(missionConfigLink)

    expect(screen.getByText('MISSION SETUP & ENVIRONMENT CONFIGURATION')).toBeInTheDocument()
  })

  it('navigates to Global Route Planner page via sidebar', () => {
    render(<App />)
    const plannerLink = screen.getByRole('link', { name: /Global Route Planner/i })
    fireEvent.click(plannerLink)

    expect(screen.getByText(/GLOBAL ROUTE PLANNER \(GA \+ 2-OPT \+ A\*\)/i)).toBeInTheDocument()
  })

  it('navigates to Live UAV Monitoring page via sidebar', () => {
    render(<App />)
    const monitoringLink = screen.getByRole('link', { name: /Live UAV Monitoring/i })
    fireEvent.click(monitoringLink)

    expect(screen.getByText('LIVE UAV SIMULATION MONITORING')).toBeInTheDocument()
  })

  it('navigates to Safety and Obstacle Monitoring page via sidebar', () => {
    render(<App />)
    const safetyLink = screen.getByRole('link', { name: /Safety & Obstacles/i })
    fireEvent.click(safetyLink)

    expect(screen.getByText(/ADAPTIVE FUZZY LOGIC \(AFL\) SAFETY LAYER/i)).toBeInTheDocument()
  })

  it('navigates to Mission Analytics page via sidebar', () => {
    render(<App />)
    const analyticsLink = screen.getByRole('link', { name: /Mission Analytics/i })
    fireEvent.click(analyticsLink)

    expect(screen.getByText('POST-FLIGHT MISSION ANALYTICS')).toBeInTheDocument()
  })

  it('navigates to Experiment Comparison page via sidebar', () => {
    render(<App />)
    const comparisonLink = screen.getByRole('link', { name: /Experiment Comparison/i })
    fireEvent.click(comparisonLink)

    expect(screen.getByText('EXPERIMENTAL FRAMEWORK COMPARISON')).toBeInTheDocument()
  })

  it('navigates to Settings page via sidebar', () => {
    render(<App />)
    const settingsLink = screen.getByRole('link', { name: /Settings/i })
    fireEvent.click(settingsLink)

    expect(screen.getByText('SYSTEM SETTINGS & INTEGRATION ENDPOINTS')).toBeInTheDocument()
  })
})
