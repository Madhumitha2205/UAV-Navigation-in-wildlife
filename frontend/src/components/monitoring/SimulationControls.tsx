import React, { useState } from 'react'
import {
  Play,
  Pause,
  Square,
  Home,
  ArrowDownToLine,
  Power,
  RotateCcw,
} from 'lucide-react'
import { Button } from '../common/Button'
import { ConfirmationDialog } from '../common/ConfirmationDialog'
import { controlApi } from '../../api/controlApi'
import { useSettingsStore } from '../../store/settingsStore'
import { useMissionStore } from '../../store/missionStore'
import { TelemetryPacket } from '../../types/telemetry'

export interface SimulationControlsProps {
  telemetry: TelemetryPacket
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({ telemetry }) => {
  const { demoMode } = useSettingsStore()
  const { addActivity } = useMissionStore()

  const [isLoading, setIsLoading] = useState(false)
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean
    title: string
    description: string
    action: () => Promise<void>
    variant: 'danger' | 'warning'
  }>({
    isOpen: false,
    title: '',
    description: '',
    action: async () => {},
    variant: 'danger',
  })

  const handleConnectToggle = async () => {
    setIsLoading(true)
    try {
      if (telemetry.simulator_connected) {
        await controlApi.disconnectSimulator(demoMode)
        addActivity({
          title: 'AirSim Disconnected',
          description: 'Simulation control link terminated',
          category: 'SIMULATION',
          severity: 'warning',
        })
      } else {
        await controlApi.connectSimulator(demoMode)
        addActivity({
          title: 'AirSim Connected',
          description: 'Control link established to multirotor',
          category: 'SIMULATION',
          severity: 'success',
        })
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleStartMission = async () => {
    setIsLoading(true)
    try {
      await controlApi.startMission('wildlife_monitoring_corridor_01', demoMode)
      addActivity({
        title: 'Mission Started',
        description: 'UAV armed, executing hierarchical navigation',
        category: 'MISSION',
        severity: 'success',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handlePauseResume = async () => {
    setIsLoading(true)
    try {
      if (telemetry.flight_state === 'HOVERING') {
        await controlApi.resumeMission(demoMode)
        addActivity({
          title: 'Mission Resumed',
          description: 'Autonomous waypoint navigation resumed',
          category: 'MISSION',
          severity: 'info',
        })
      } else {
        await controlApi.pauseMission(demoMode)
        addActivity({
          title: 'Mission Paused',
          description: 'UAV holding position (hovering)',
          category: 'MISSION',
          severity: 'warning',
        })
      }
    } finally {
      setIsLoading(false)
    }
  }

  const triggerStopDialog = () => {
    setConfirmDialog({
      isOpen: true,
      title: 'Abort Autonomous Mission?',
      description:
        'This will immediately cancel autonomous trajectory tracking and switch multirotor control to emergency safe hover or descent.',
      variant: 'danger',
      action: async () => {
        await controlApi.stopMission(demoMode)
        addActivity({
          title: 'Mission Aborted',
          description: 'Emergency stop command dispatched to controller',
          category: 'MISSION',
          severity: 'danger',
        })
      },
    })
  }

  const triggerRTLDialog = () => {
    setConfirmDialog({
      isOpen: true,
      title: 'Initiate Return to Launch (RTL)?',
      description:
        'The UAV will climb to the safety transit altitude and navigate directly to the initial mission takeoff point.',
      variant: 'warning',
      action: async () => {
        await controlApi.returnToLand(demoMode)
        addActivity({
          title: 'RTL Command Executed',
          description: 'UAV returning to start coordinates',
          category: 'MISSION',
          severity: 'warning',
        })
      },
    })
  }

  const triggerLandDialog = () => {
    setConfirmDialog({
      isOpen: true,
      title: 'Initiate Immediate Landing?',
      description:
        'The UAV will decelerate horizontal velocity to zero and commence vertical descent to ground level.',
      variant: 'warning',
      action: async () => {
        await controlApi.landUAV(demoMode)
        addActivity({
          title: 'Landing Sequence Commenced',
          description: 'Autonomous descent initiated',
          category: 'SIMULATION',
          severity: 'warning',
        })
      },
    })
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-2 p-3 bg-[#0d1424] border border-slate-800 rounded-xl">
        <Button
          variant={telemetry.simulator_connected ? 'secondary' : 'primary'}
          size="sm"
          onClick={handleConnectToggle}
          disabled={isLoading}
        >
          <Power className="w-3.5 h-3.5 mr-1" />
          {telemetry.simulator_connected ? 'Disconnect Sim' : 'Connect AirSim'}
        </Button>

        <div className="w-[1px] h-5 bg-slate-800 mx-1 hidden sm:block" />

        <Button
          variant="safe"
          size="sm"
          onClick={handleStartMission}
          disabled={isLoading || !telemetry.simulator_connected}
        >
          <Play className="w-3.5 h-3.5 mr-1" />
          Start Mission
        </Button>

        <Button
          variant="secondary"
          size="sm"
          onClick={handlePauseResume}
          disabled={isLoading || !telemetry.simulator_connected}
        >
          {telemetry.flight_state === 'HOVERING' ? (
            <>
              <Play className="w-3.5 h-3.5 mr-1" />
              Resume
            </>
          ) : (
            <>
              <Pause className="w-3.5 h-3.5 mr-1" />
              Pause
            </>
          )}
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={triggerRTLDialog}
          disabled={isLoading || !telemetry.simulator_connected}
        >
          <Home className="w-3.5 h-3.5 mr-1" />
          RTL
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={triggerLandDialog}
          disabled={isLoading || !telemetry.simulator_connected}
        >
          <ArrowDownToLine className="w-3.5 h-3.5 mr-1" />
          Land
        </Button>

        <Button
          variant="danger"
          size="sm"
          onClick={triggerStopDialog}
          disabled={isLoading || !telemetry.simulator_connected}
          className="ml-auto"
        >
          <Square className="w-3.5 h-3.5 mr-1" />
          Stop Mission
        </Button>
      </div>

      <ConfirmationDialog
        isOpen={confirmDialog.isOpen}
        title={confirmDialog.title}
        description={confirmDialog.description}
        variant={confirmDialog.variant}
        onConfirm={async () => {
          setIsLoading(true)
          try {
            await confirmDialog.action()
          } finally {
            setIsLoading(false)
            setConfirmDialog((prev) => ({ ...prev, isOpen: false }))
          }
        }}
        onCancel={() => setConfirmDialog((prev) => ({ ...prev, isOpen: false }))}
        isLoading={isLoading}
      />
    </>
  )
}
