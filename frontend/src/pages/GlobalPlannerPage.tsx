import React, { useState } from 'react'
import {
  Route,
  Play,
  RotateCcw,
  Layers,
  Compass,
  MapPin,
  Flag,
  Plus,
  Trash2,
  ArrowUpDown,
  Edit2,
  Check,
  Search,
  Sparkles,
} from 'lucide-react'
import { useMissionStore } from '../store/missionStore'
import { useSettingsStore } from '../store/settingsStore'
import { IndiaLeafletMap } from '../components/map/IndiaLeafletMap'
import { EnvironmentMap } from '../components/planner/EnvironmentMap'
import { RouteMetrics } from '../components/planner/RouteMetrics'
import { FitnessChart } from '../components/planner/FitnessChart'
import { Button } from '../components/common/Button'
import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { GeoCoordinate, haversineDistanceM } from '../utils/geoUtils'
import { MonitoringWaypoint } from '../types/environment'

export const GlobalPlannerPage: React.FC = () => {
  const { environmentConfig, currentRoutePlan, isPlanning, planRoute, updateEnvironment, addWaypoint, removeWaypoint } =
    useMissionStore()
  const { demoMode } = useSettingsStore()

  const [viewMode, setViewMode] = useState<'INDIA_MAP' | 'LOCAL_CANVAS'>('INDIA_MAP')
  const [mapInteractionMode, setMapInteractionMode] = useState<'SELECT_START' | 'SELECT_DEST' | 'ADD_WAYPOINT' | 'VIEW'>('ADD_WAYPOINT')
  const [showManualModal, setShowManualModal] = useState(false)
  const [manualCoord, setManualCoord] = useState<{ lat: string; lon: string; alt: string; name: string }>({
    lat: '26.5775',
    lon: '93.1711',
    alt: '10.0',
    name: 'Sector Point',
  })

  // Start & Destination as GeoCoordinates
  const startGeo: GeoCoordinate = {
    lat: environmentConfig.start_position.lat ?? 26.5775,
    lon: environmentConfig.start_position.lon ?? 93.1711,
    alt: environmentConfig.start_position.z,
    name: 'Kaziranga West Command Hub',
  }

  const destGeo: GeoCoordinate = {
    lat: environmentConfig.destination.lat ?? 26.6500,
    lon: environmentConfig.destination.lon ?? 93.2500,
    alt: environmentConfig.destination.z,
    name: 'Kaziranga East Outpost',
  }

  // Waypoints as GeoCoordinates
  const waypointsGeo: GeoCoordinate[] = environmentConfig.monitoring_waypoints.map((w, i) => ({
    lat: w.lat ?? 26.589 + i * 0.009,
    lon: w.lon ?? 93.182 + i * 0.009,
    alt: w.z,
    name: w.zone_name,
  }))

  const handleStartChange = (coord: GeoCoordinate) => {
    updateEnvironment({
      start_position: {
        ...environmentConfig.start_position,
        lat: coord.lat,
        lon: coord.lon,
        z: coord.alt ?? 10.0,
      },
    })
  }

  const handleDestChange = (coord: GeoCoordinate) => {
    updateEnvironment({
      destination: {
        ...environmentConfig.destination,
        lat: coord.lat,
        lon: coord.lon,
        z: coord.alt ?? 10.0,
      },
    })
  }

  const handleWaypointAdd = (coord: GeoCoordinate) => {
    const id = `WP_${environmentConfig.monitoring_waypoints.length + 1}`
    const newWp: MonitoringWaypoint = {
      id,
      zone_name: coord.name || `Waypoint ${environmentConfig.monitoring_waypoints.length + 1}`,
      x: 10.0 + environmentConfig.monitoring_waypoints.length * 12.0,
      y: 15.0 + environmentConfig.monitoring_waypoints.length * 8.0,
      z: coord.alt ?? 10.0,
      lat: coord.lat,
      lon: coord.lon,
      priority: 1,
    }
    addWaypoint(newWp)
  }

  const handleWaypointUpdate = (idx: number, coord: GeoCoordinate) => {
    const wp = environmentConfig.monitoring_waypoints[idx]
    if (!wp) return
    const updated = environmentConfig.monitoring_waypoints.map((item, i) =>
      i === idx ? { ...item, lat: coord.lat, lon: coord.lon, z: coord.alt ?? item.z } : item
    )
    updateEnvironment({ monitoring_waypoints: updated })
  }

  const handleWaypointRemove = (idx: number) => {
    const wp = environmentConfig.monitoring_waypoints[idx]
    if (wp) removeWaypoint(wp.id)
  }

  const handleMoveWaypoint = (fromIdx: number, toIdx: number) => {
    if (toIdx < 0 || toIdx >= environmentConfig.monitoring_waypoints.length) return
    const list = [...environmentConfig.monitoring_waypoints]
    const [moved] = list.splice(fromIdx, 1)
    list.splice(toIdx, 0, moved)
    updateEnvironment({ monitoring_waypoints: list })
  }

  const handleManualAdd = () => {
    const lat = parseFloat(manualCoord.lat)
    const lon = parseFloat(manualCoord.lon)
    const alt = parseFloat(manualCoord.alt) || 10.0
    if (!isNaN(lat) && !isNaN(lon)) {
      handleWaypointAdd({ lat, lon, alt, name: manualCoord.name })
      setShowManualModal(false)
    }
  }

  const handleResetRoute = () => {
    useMissionStore.getState().resetToDefaults()
  }

  return (
    <div className="space-y-6">
      {/* Top Planner Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-[#0c1424] border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-slate-100 tracking-wide flex items-center gap-2">
              <Route className="w-5 h-5 text-sky-400" />
              GLOBAL ROUTE PLANNER (GA + 2-OPT + A*) — INDIA MAP
            </h1>
            {demoMode ? (
              <Badge variant="demo">STANDALONE DEMO</Badge>
            ) : (
              <Badge variant="safe">LIVE PYTHON GA BACKEND</Badge>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real geographical India map with OpenStreetMap tiles: Select start, destination, and waypoints anywhere in
            India. Converts GPS coordinates to local simulation coordinates, and optimizes routes using Genetic Algorithm,
            2-Opt local search, and A* obstacle avoidance.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-mono">
            <button
              onClick={() => setViewMode('INDIA_MAP')}
              className={`px-3 py-1 rounded transition-colors ${
                viewMode === 'INDIA_MAP'
                  ? 'bg-sky-600 text-white font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              India Leaflet Map
            </button>
            <button
              onClick={() => setViewMode('LOCAL_CANVAS')}
              className={`px-3 py-1 rounded transition-colors ${
                viewMode === 'LOCAL_CANVAS'
                  ? 'bg-sky-600 text-white font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              2D Metric Radar
            </button>
          </div>

          <Button
            variant="primary"
            size="sm"
            onClick={() => planRoute()}
            isLoading={isPlanning}
          >
            <Play className="w-3.5 h-3.5 mr-1" />
            Plan Route (GA + 2-Opt)
          </Button>

          <Button variant="outline" size="sm" onClick={handleResetRoute}>
            <RotateCcw className="w-3.5 h-3.5 mr-1" />
            Reset
          </Button>
        </div>
      </div>

      {/* Route Performance Metrics Bar */}
      <RouteMetrics routePlan={currentRoutePlan} />

      {/* Main Map Viewport */}
      {viewMode === 'INDIA_MAP' ? (
        <div className="space-y-4">
          <IndiaLeafletMap
            routePlan={currentRoutePlan}
            startPoint={startGeo}
            destination={destGeo}
            waypoints={waypointsGeo}
            onStartChange={handleStartChange}
            onDestinationChange={handleDestChange}
            onWaypointAdd={handleWaypointAdd}
            onWaypointUpdate={handleWaypointUpdate}
            onWaypointRemove={handleWaypointRemove}
            mode={mapInteractionMode}
            onModeChange={setMapInteractionMode}
            height={560}
          />
        </div>
      ) : (
        <Card
          title="2D Metric Canvas Radar (Local Grid)"
          subtitle="Direct local coordinate inspection view in standard Cartesian frame"
          icon={<Compass className="w-4 h-4 text-cyan-400" />}
        >
          <EnvironmentMap routePlan={currentRoutePlan} height={520} />
        </Card>
      )}

      {/* Mission Waypoints Management & Coordinate Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Waypoint Sequence Editor */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-[#0c1424] border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-sky-400" />
              <h3 className="text-sm font-bold text-slate-100 font-mono">MISSION WAYPOINTS SEQUENCE</h3>
              <Badge variant="primary">{environmentConfig.monitoring_waypoints.length} WAYPOINTS</Badge>
            </div>
            <button
              onClick={() => setShowManualModal(true)}
              className="px-3 py-1 rounded bg-sky-600/20 border border-sky-500/40 text-sky-300 hover:bg-sky-600/30 text-xs font-mono flex items-center gap-1.5 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              Enter Coordinates Manually
            </button>
          </div>

          {/* Waypoints List */}
          <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
            {/* Start Row */}
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-emerald-950/30 border border-emerald-500/30 font-mono text-xs">
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full bg-emerald-500/20 border border-emerald-400 text-emerald-300 flex items-center justify-center font-bold text-[10px]">
                  S
                </span>
                <div>
                  <span className="text-emerald-300 font-semibold">{startGeo.name}</span>
                  <div className="text-[10px] text-slate-400">
                    Lat: {startGeo.lat.toFixed(5)}° N, Lon: {startGeo.lon.toFixed(5)}° E (Alt: {startGeo.alt}m)
                  </div>
                </div>
              </div>
              <Badge variant="safe">START</Badge>
            </div>

            {/* Monitoring Waypoints */}
            {environmentConfig.monitoring_waypoints.map((wp, idx) => (
              <div
                key={wp.id}
                className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-colors font-mono text-xs"
              >
                <div className="flex items-center gap-3">
                  <span className="w-6 h-6 rounded-full bg-sky-500/20 border border-sky-400 text-sky-300 flex items-center justify-center font-bold text-[10px]">
                    {idx + 1}
                  </span>
                  <div>
                    <span className="text-slate-200 font-semibold">{wp.zone_name}</span>
                    <div className="text-[10px] text-slate-400">
                      Lat: {wp.lat?.toFixed(5) ?? '26.589'}° N, Lon: {wp.lon?.toFixed(5) ?? '93.182'}° E (Alt: {wp.z}m)
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleMoveWaypoint(idx, idx - 1)}
                    disabled={idx === 0}
                    className="p-1 text-slate-400 hover:text-slate-200 disabled:opacity-30"
                    title="Move Up"
                  >
                    ▲
                  </button>
                  <button
                    onClick={() => handleMoveWaypoint(idx, idx + 1)}
                    disabled={idx === environmentConfig.monitoring_waypoints.length - 1}
                    className="p-1 text-slate-400 hover:text-slate-200 disabled:opacity-30"
                    title="Move Down"
                  >
                    ▼
                  </button>
                  <button
                    onClick={() => handleWaypointRemove(idx)}
                    className="p-1 text-rose-400 hover:text-rose-300 ml-1"
                    title="Delete Waypoint"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}

            {/* Destination Row */}
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-rose-950/30 border border-rose-500/30 font-mono text-xs">
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full bg-rose-500/20 border border-rose-500 text-rose-300 flex items-center justify-center font-bold text-[10px]">
                  D
                </span>
                <div>
                  <span className="text-rose-300 font-semibold">{destGeo.name}</span>
                  <div className="text-[10px] text-slate-400">
                    Lat: {destGeo.lat.toFixed(5)}° N, Lon: {destGeo.lon.toFixed(5)}° E (Alt: {destGeo.alt}m)
                  </div>
                </div>
              </div>
              <Badge variant="danger">DESTINATION</Badge>
            </div>
          </div>
        </div>

        {/* Right: GA Convergence & Hyperparameters */}
        <div className="p-5 rounded-xl bg-[#0c1424] border border-slate-800 space-y-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-sky-400" />
            <h3 className="text-sm font-bold text-slate-100 font-mono">GENETIC ALGORITHM CONVERGENCE</h3>
          </div>

          {currentRoutePlan?.fitness_history && currentRoutePlan.fitness_history.length > 0 ? (
            <FitnessChart data={currentRoutePlan.fitness_history} />
          ) : (
            <div className="h-44 flex items-center justify-center text-xs font-mono text-slate-500 border border-dashed border-slate-800 rounded-lg">
              Run route planning to view GA evolution curve
            </div>
          )}

          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-[11px] font-mono space-y-1 text-slate-400">
            <div>
              Population:{' '}
              <span className="text-slate-200">{environmentConfig.planning_params.population_size}</span>
            </div>
            <div>
              Generations:{' '}
              <span className="text-slate-200">{environmentConfig.planning_params.max_generations}</span>
            </div>
            <div>
              2-Opt Refinement:{' '}
              <span className="text-emerald-400 font-semibold">Active every {environmentConfig.planning_params.two_opt_frequency} gens</span>
            </div>
          </div>
        </div>
      </div>

      {/* Manual Coordinate Entry Modal */}
      {showManualModal && (
        <div className="fixed inset-0 z-[2000] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm select-none">
          <div className="w-full max-w-md rounded-2xl bg-[#0c1424] border border-slate-700 shadow-2xl p-6 font-sans space-y-4">
            <h3 className="text-sm font-bold text-slate-100 font-mono flex items-center gap-2">
              <MapPin className="w-4 h-4 text-sky-400" />
              Enter Manual Geographical Coordinates
            </h3>
            <p className="text-xs text-slate-400">
              Input precision WGS-84 latitude and longitude coordinates anywhere in India.
            </p>

            <div className="space-y-3 font-mono text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Waypoint Label / Zone Name:</label>
                <input
                  type="text"
                  value={manualCoord.name}
                  onChange={(e) => setManualCoord({ ...manualCoord, name: e.target.value })}
                  className="w-full p-2 rounded bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-sky-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Latitude (°N):</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={manualCoord.lat}
                    onChange={(e) => setManualCoord({ ...manualCoord, lat: e.target.value })}
                    className="w-full p-2 rounded bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Longitude (°E):</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={manualCoord.lon}
                    onChange={(e) => setManualCoord({ ...manualCoord, lon: e.target.value })}
                    className="w-full p-2 rounded bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Flight Altitude (m):</label>
                <input
                  type="number"
                  value={manualCoord.alt}
                  onChange={(e) => setManualCoord({ ...manualCoord, alt: e.target.value })}
                  className="w-full p-2 rounded bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-sky-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowManualModal(false)}
                className="px-4 py-2 rounded bg-slate-800 text-slate-400 hover:text-slate-200 text-xs font-mono"
              >
                Cancel
              </button>
              <button
                onClick={handleManualAdd}
                className="px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 text-white text-xs font-mono font-semibold"
              >
                Add to Route
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
