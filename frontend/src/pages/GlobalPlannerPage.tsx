import React, { useState } from 'react'
import { Route, Play, RefreshCw, Layers, Compass } from 'lucide-react'
import { useMissionStore } from '../store/missionStore'
import { useSettingsStore } from '../store/settingsStore'
import { EnvironmentMap } from '../components/planner/EnvironmentMap'
import { RouteMetrics } from '../components/planner/RouteMetrics'
import { RouteLegend } from '../components/planner/RouteLegend'
import { FitnessChart } from '../components/planner/FitnessChart'
import { Button } from '../components/common/Button'
import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { MonitoringWaypoint, StaticObstacle } from '../types/environment'

export const GlobalPlannerPage: React.FC = () => {
  const { currentRoutePlan, isPlanning, planRoute } = useMissionStore()
  const { demoMode } = useSettingsStore()

  const [selectedWaypoint, setSelectedWaypoint] = useState<MonitoringWaypoint | null>(null)
  const [selectedObstacle, setSelectedObstacle] = useState<StaticObstacle | null>(null)

  return (
    <div className="space-y-6">
      {/* Top Planner Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-[#0c1424] border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-slate-100 tracking-wide flex items-center gap-2">
              <Route className="w-5 h-5 text-sky-400" />
              GLOBAL ROUTE PLANNER (GA + 2-OPT + A*)
            </h1>
            {demoMode ? (
              <Badge variant="demo">DEMO ROUTE</Badge>
            ) : (
              <Badge variant="safe">LIVE GA RESULT</Badge>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Hierarchical global trajectory optimization: GA explores discrete monitoring sequences, 2-Opt removes tour crossings, and A* constructs collision-free corridor segments.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => planRoute()}
            isLoading={isPlanning}
          >
            <Play className="w-3.5 h-3.5 mr-1" />
            Re-optimize Route
          </Button>
        </div>
      </div>

      {/* Route Performance Metrics Bar */}
      <RouteMetrics routePlan={currentRoutePlan} />

      {/* Main Map Visualization Area */}
      <Card
        title="Interactive 2D Global Planner Viewport"
        subtitle="Use mouse drag to pan, scroll to zoom, click elements to inspect, and use top buttons to toggle layer overlays"
        icon={<Compass className="w-4 h-4 text-cyan-400" />}
      >
        <EnvironmentMap
          routePlan={currentRoutePlan}
          height={520}
          onSelectWaypoint={(wp) => {
            setSelectedWaypoint(wp)
            setSelectedObstacle(null)
          }}
          onSelectObstacle={(obs) => {
            setSelectedObstacle(obs)
            setSelectedWaypoint(null)
          }}
          selectedWaypointId={selectedWaypoint?.id}
          selectedObstacleId={selectedObstacle?.id}
        />
      </Card>

      {/* Map Legend */}
      <RouteLegend />

      {/* GA Fitness Evolution History & Selected Element Inspection */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <FitnessChart data={currentRoutePlan?.fitness_history} />
        </div>

        {/* Selected Element Detail Inspector */}
        <div className="lg:col-span-1">
          <Card
            title="Spatial Entity Inspector"
            subtitle="Details of selected waypoint or hazard"
            icon={<Layers className="w-4 h-4 text-sky-400" />}
          >
            {selectedWaypoint ? (
              <div className="space-y-3 text-xs font-mono">
                <div className="flex justify-between pb-2 border-b border-slate-800">
                  <span className="text-slate-400">WAYPOINT ID:</span>
                  <span className="text-cyan-400 font-bold">{selectedWaypoint.id}</span>
                </div>
                <div className="flex justify-between pb-2 border-b border-slate-800">
                  <span className="text-slate-400">HABITAT ZONE:</span>
                  <span className="text-slate-200">{selectedWaypoint.zone_name}</span>
                </div>
                <div className="flex justify-between pb-2 border-b border-slate-800">
                  <span className="text-slate-400">COORDINATES:</span>
                  <span className="text-slate-200">
                    [{selectedWaypoint.x}, {selectedWaypoint.y}, {selectedWaypoint.z}]
                  </span>
                </div>
                <div className="flex justify-between pb-2 border-b border-slate-800">
                  <span className="text-slate-400">IMPORTANCE / PRIORITY:</span>
                  <Badge variant={selectedWaypoint.priority === 1 ? 'danger' : 'warning'}>
                    Priority {selectedWaypoint.priority}
                  </Badge>
                </div>
              </div>
            ) : selectedObstacle ? (
              <div className="space-y-3 text-xs font-mono">
                <div className="flex justify-between pb-2 border-b border-slate-800">
                  <span className="text-slate-400">HAZARD ID:</span>
                  <span className="text-rose-400 font-bold">{selectedObstacle.id}</span>
                </div>
                <div className="flex justify-between pb-2 border-b border-slate-800">
                  <span className="text-slate-400">GEOMETRY:</span>
                  <Badge variant="danger">{selectedObstacle.type.toUpperCase()}</Badge>
                </div>
                {selectedObstacle.type === 'circle' ? (
                  <>
                    <div className="flex justify-between pb-2 border-b border-slate-800">
                      <span className="text-slate-400">CENTER COORDS:</span>
                      <span className="text-slate-200">
                        [{selectedObstacle.x}, {selectedObstacle.y}]
                      </span>
                    </div>
                    <div className="flex justify-between pb-2 border-b border-slate-800">
                      <span className="text-slate-400">RADIUS:</span>
                      <span className="text-slate-200">{selectedObstacle.radius} metres</span>
                    </div>
                  </>
                ) : (
                  <div className="flex justify-between pb-2 border-b border-slate-800">
                    <span className="text-slate-400">BOUNDS:</span>
                    <span className="text-slate-200">
                      [{selectedObstacle.min_x}, {selectedObstacle.min_y}] to [
                      {selectedObstacle.max_x}, {selectedObstacle.max_y}]
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-10 text-slate-500 text-xs font-mono">
                Click on any waypoint or obstacle in the 2D map to inspect coordinates, priority, and bounds.
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
