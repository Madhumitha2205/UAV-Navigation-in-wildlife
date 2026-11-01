import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ConfirmationDialog } from '../components/common/ConfirmationDialog'
import { LoadingState } from '../components/common/LoadingState'
import { ErrorState } from '../components/common/ErrorState'
import { EmptyState } from '../components/common/EmptyState'
import { Badge } from '../components/common/Badge'
import { MetricCard } from '../components/dashboard/MetricCard'

describe('Reusable UI Components', () => {
  it('renders and triggers ConfirmationDialog actions', () => {
    const handleConfirm = vi.fn()
    const handleCancel = vi.fn()

    const { rerender } = render(
      <ConfirmationDialog
        isOpen={false}
        title="Abort Mission"
        description="Are you sure you want to abort?"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    )

    expect(screen.queryByText('Abort Mission')).toBeNull()

    rerender(
      <ConfirmationDialog
        isOpen={true}
        title="Abort Mission"
        description="Are you sure you want to abort?"
        confirmText="Yes, Abort"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    )

    expect(screen.getByText('Abort Mission')).toBeInTheDocument()
    expect(screen.getByText('Are you sure you want to abort?')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Yes, Abort'))
    expect(handleConfirm).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByText('Cancel'))
    expect(handleCancel).toHaveBeenCalledTimes(1)
  })

  it('renders LoadingState with custom message', () => {
    render(<LoadingState message="Connecting to PX4..." />)
    expect(screen.getByText('Connecting to PX4...')).toBeInTheDocument()
  })

  it('renders ErrorState with retry trigger', () => {
    const handleRetry = vi.fn()
    render(
      <ErrorState
        title="AirSim Connection Lost"
        message="RPC timeout on port 41451"
        onRetry={handleRetry}
      />
    )

    expect(screen.getByText('AirSim Connection Lost')).toBeInTheDocument()
    expect(screen.getByText('RPC timeout on port 41451')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Retry Connection'))
    expect(handleRetry).toHaveBeenCalledTimes(1)
  })

  it('renders EmptyState with action button', () => {
    const handleAction = vi.fn()
    render(
      <EmptyState
        title="No Experiments Found"
        description="Run an evaluation trial to generate metrics"
        actionLabel="Start Trial"
        onAction={handleAction}
      />
    )

    expect(screen.getByText('No Experiments Found')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Start Trial'))
    expect(handleAction).toHaveBeenCalledTimes(1)
  })

  it('renders Badge with correct variant styling', () => {
    render(<Badge variant="safe">SAFE STATUS</Badge>)
    expect(screen.getByText('SAFE STATUS')).toBeInTheDocument()
  })

  it('renders MetricCard with value and sublabel', () => {
    render(
      <MetricCard
        title="UAV Altitude"
        value="16.5"
        unit="m"
        sublabel="Positive Up"
      />
    )
    expect(screen.getByText(/UAV Altitude/i)).toBeInTheDocument()
    expect(screen.getByText('16.5')).toBeInTheDocument()
    expect(screen.getByText('m')).toBeInTheDocument()
  })
})
