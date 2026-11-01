import React, { useState } from 'react'
import {
  Save,
  RotateCcw,
  Play,
  AlertCircle,
  CheckCircle2,
  Sliders,
  MapPin,
} from 'lucide-react'
import { useMissionStore } from '../store/missionStore'
import { EnvironmentForm } from '../components/mission/EnvironmentForm'
import { WaypointTable } from '../components/mission/WaypointTable'
import { ObstacleForm } from '../components/mission/ObstacleForm'
import { PlanningParamsForm } from '../components/mission/PlanningParamsForm'
import { EnvironmentMap } from '../components/planner/EnvironmentMap'
import { EnvironmentConfigSchema } from '../utils/validators'
import { Button } from '../components/common/Button'
import { Card } from '../components/common/Card'

export const MissionConfigurationPage: React.FC = () => {
  const {
    environmentConfig,
    updateEnvironment,
    addWaypoint,
    updateWaypoint,
    removeWaypoint,
    addObstacle,
    removeObstacle,
    updatePlanningParams,
    planRoute,
    resetToDefaults,
    isPlanning,
    planningError,
    currentRoutePlan,
    addActivity,
  } = useMissionStore()

  const [validationErrors, setValidationErrors] = useState<string[]>([])
  const [saveSuccess, setSaveSuccess] = useState(false)

  const handleValidateAndGenerate = async () => {
    setValidationErrors([])
    const validation = EnvironmentConfigSchema.safeParse(environmentConfig)

    if (!validation.success) {
      const errors = validation.error.issues.map(
        (issue) => `${issue.path.join('.')}: ${issue.message}`
      )
      setValidationErrors(errors)
      return
    }

    await planRoute()
  }

  const handleSaveConfiguration = () => {
    const validation = EnvironmentConfigSchema.safeParse(environmentConfig)
    if (!validation.success) {
      const errors = validation.error.issues.map(
        (issue) => `${issue.path.join('.')}: ${issue.message}`
      )
      setValidationErrors(errors)
      return
    }
    setValidationErrors([])
    setSaveSuccess(true)
    addActivity({
      title: 'Configuration Saved',
      description: `Environment bounds ${environmentConfig.width}x${environmentConfig.height}m and ${environmentConfig.monitoring_waypoints.length} waypoints saved`,
      category: 'MISSION',
      severity: 'info',
    })
    setTimeout(() => setSaveSuccess(false), 3000)
  }

  return (
    <div className="space-y-6">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-[#0c1424] border border-slate-800">
        <div>
          <h1 className="text-lg font-bold text-slate-100 tracking-wide flex items-center gap-2">
            <Sliders className="w-5 h-5 text-sky-400" />
            MISSION SETUP & ENVIRONMENT CONFIGURATION
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Define survey corridors, monitoring waypoints, forest obstacles, and GA hyperparameters
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={resetToDefaults} disabled={isPlanning}>
            <RotateCcw className="w-3.5 h-3.5 mr-1" />
            Reset Config
          </Button>

          <Button variant="secondary" size="sm" onClick={handleSaveConfiguration} disabled={isPlanning}>
            <Save className="w-3.5 h-3.5 mr-1" />
            Save Config
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleValidateAndGenerate}
            isLoading={isPlanning}
          >
            <Play className="w-3.5 h-3.5 mr-1" />
            Generate Route
          </Button>
        </div>
      </div>

      {/* Save Success Alert */}
      {saveSuccess && (
        <div className="flex items-center gap-2 p-3 bg-emerald-950/40 border border-emerald-800/80 rounded-lg text-xs text-emerald-300 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Configuration saved successfully and cached for planner execution.</span>
        </div>
      )}

      {/* Validation Errors Notice */}
      {validationErrors.length > 0 && (
        <div className="p-3 bg-rose-950/40 border border-rose-800/80 rounded-lg text-xs text-rose-300 space-y-1 animate-in fade-in">
          <div className="flex items-center gap-2 font-bold font-mono">
            <AlertCircle className="w-4 h-4 text-rose-400" />
            <span>Invalid Configuration Parameters:</span>
          </div>
          <ul className="list-disc pl-5 space-y-0.5 text-[11px] text-rose-200">
            {validationErrors.map((err, idx) => (
              <li key={idx}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Planning API Error Notice */}
      {planningError && (
        <div className="p-3 bg-rose-950/40 border border-rose-800/80 rounded-lg text-xs text-rose-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400" />
          <span>{planningError}</span>
        </div>
      )}

      {/* Section 1: Dimensions & Coordinates */}
      <EnvironmentForm config={environmentConfig} onChange={updateEnvironment} />

      {/* Section 2: Monitoring Waypoints & Interactive Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <WaypointTable
          waypoints={environmentConfig.monitoring_waypoints}
          onAddWaypoint={addWaypoint}
          onUpdateWaypoint={updateWaypoint}
          onRemoveWaypoint={removeWaypoint}
        />

        <Card
          title="Spatial Configuration Preview"
          subtitle="Click on map to position waypoints or inspect coordinate alignment"
          icon={<MapPin className="w-4 h-4 text-sky-400" />}
        >
          <EnvironmentMap
            routePlan={currentRoutePlan}
            height={360}
            allowMapClickToAdd={true}
            onAddPoint={(pt) => {
              addWaypoint({
                id: `WP_${environmentConfig.monitoring_waypoints.length + 1}`,
                zone_name: 'Survey_Waypoint',
                x: pt.x,
                y: pt.y,
                z: 16.0,
                priority: 2,
              })
            }}
          />
        </Card>
      </div>

      {/* Section 3: Geometric Obstacles & Hazards */}
      <ObstacleForm
        obstacles={environmentConfig.obstacles}
        onAddObstacle={addObstacle}
        onRemoveObstacle={removeObstacle}
      />

      {/* Section 4: GA + 2-Opt Planner Parameters */}
      <PlanningParamsForm
        params={environmentConfig.planning_params}
        onChange={updatePlanningParams}
        onResetDefaults={resetToDefaults}
        onGenerateRoute={handleValidateAndGenerate}
        isPlanning={isPlanning}
      />
    </div>
  )
}
