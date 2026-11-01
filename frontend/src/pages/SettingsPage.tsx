import React, { useState } from 'react'
import { Settings, Save, RotateCcw, CheckCircle2, Server, Globe } from 'lucide-react'
import { useSettingsStore } from '../store/settingsStore'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'

export const SettingsPage: React.FC = () => {
  const {
    demoMode,
    globalApiUrl,
    controlApiUrl,
    wsUrl,
    units,
    setDemoMode,
    setGlobalApiUrl,
    setControlApiUrl,
    setWsUrl,
    setUnits,
    resetDefaults,
  } = useSettingsStore()

  const [formGlobalApi, setFormGlobalApi] = useState(globalApiUrl)
  const [formControlApi, setFormControlApi] = useState(controlApiUrl)
  const [formWsUrl, setFormWsUrl] = useState(wsUrl)
  const [savedSuccess, setSavedSuccess] = useState(false)

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    setGlobalApiUrl(formGlobalApi)
    setControlApiUrl(formControlApi)
    setWsUrl(formWsUrl)
    setSavedSuccess(true)
    setTimeout(() => setSavedSuccess(false), 3000)
  }

  const handleReset = () => {
    resetDefaults()
    setFormGlobalApi('http://localhost:8000')
    setFormControlApi('http://localhost:8001')
    setFormWsUrl('ws://localhost:8001/ws/telemetry')
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-[#0c1424] border border-slate-800">
        <div>
          <h1 className="text-lg font-bold text-slate-100 tracking-wide flex items-center gap-2">
            <Settings className="w-5 h-5 text-sky-400" />
            SYSTEM SETTINGS & INTEGRATION ENDPOINTS
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Configure REST API endpoints, WebSocket streams, coordinate conventions, and operation mode
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleReset}>
            <RotateCcw className="w-3.5 h-3.5 mr-1" />
            Reset Defaults
          </Button>
          <Button variant="primary" size="sm" onClick={handleSave}>
            <Save className="w-3.5 h-3.5 mr-1" />
            Save Changes
          </Button>
        </div>
      </div>

      {savedSuccess && (
        <div className="flex items-center gap-2 p-3 bg-emerald-950/40 border border-emerald-800/80 rounded-lg text-xs text-emerald-300">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>System integration endpoints successfully updated and persisted.</span>
        </div>
      )}

      {/* Operation Mode Selector */}
      <Card
        title="Application Operation Mode"
        subtitle="Switch between fully standalone simulated demo mode and live Python backend connection"
        icon={<Globe className="w-4 h-4 text-cyan-400" />}
      >
        <div className="flex items-center justify-between p-4 bg-slate-900/60 border border-slate-800 rounded-lg">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-200">Current Mode:</span>
              {demoMode ? (
                <Badge variant="demo" pulse>
                  SIMULATED DEMO MODE
                </Badge>
              ) : (
                <Badge variant="safe" pulse>
                  LIVE BACKEND CONNECTION
                </Badge>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-lg">
              {demoMode
                ? 'Demo mode allows interactive review of all 8 pages with simulated GA routes, dynamic telemetry streams, and comparative metrics without requiring backend servers.'
                : 'Live mode dispatches real HTTP REST requests to the GA Route Planner and AirSim/TD3 controller APIs, and streams telemetry via WebSocket.'}
            </p>
          </div>

          <Button
            variant={demoMode ? 'secondary' : 'safe'}
            size="sm"
            onClick={() => setDemoMode(!demoMode)}
          >
            {demoMode ? 'Switch to Live Mode' : 'Switch to Demo Mode'}
          </Button>
        </div>
      </Card>

      {/* Backend API Endpoints Form */}
      <form onSubmit={handleSave}>
        <Card
          title="Backend REST & WebSocket Endpoints"
          subtitle="Configure ports and hostnames for Part 1 (Global Planner) and Part 2 (Local Controller & AirSim)"
          icon={<Server className="w-4 h-4 text-purple-400" />}
        >
          <div className="space-y-4 text-xs font-mono">
            <div>
              <label className="block text-slate-400 mb-1">
                GLOBAL PLANNER API (PART 1) — REST URL:
              </label>
              <input
                type="text"
                value={formGlobalApi}
                onChange={(e) => setFormGlobalApi(e.target.value)}
                placeholder="http://localhost:8000"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-sky-500 focus:outline-none"
              />
              <span className="text-[10px] text-slate-500 font-sans mt-0.5 block">
                Target endpoint for POST /api/planner/plan and GET /api/planner/route
              </span>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">
                AIRSIM / TD3 CONTROLLER API (PART 2) — REST URL:
              </label>
              <input
                type="text"
                value={formControlApi}
                onChange={(e) => setFormControlApi(e.target.value)}
                placeholder="http://localhost:8001"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-sky-500 focus:outline-none"
              />
              <span className="text-[10px] text-slate-500 font-sans mt-0.5 block">
                Target endpoint for simulation status, arming, mission dispatch, and flight commands
              </span>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">
                REAL-TIME TELEMETRY WEBSOCKET URL:
              </label>
              <input
                type="text"
                value={formWsUrl}
                onChange={(e) => setFormWsUrl(e.target.value)}
                placeholder="ws://localhost:8001/ws/telemetry"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-sky-500 focus:outline-none"
              />
              <span className="text-[10px] text-slate-500 font-sans mt-0.5 block">
                High-frequency JSON telemetry stream publishing multirotor kinematics and safety vectors
              </span>
            </div>
          </div>
        </Card>
      </form>

      {/* Units & Coordinate Convention */}
      <Card title="Units & Coordinate Conventions">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
          <div>
            <label className="block text-slate-400 mb-1">MEASUREMENT UNITS:</label>
            <select
              value={units}
              onChange={(e) => setUnits(e.target.value as any)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-sky-500"
            >
              <option value="metric">Metric (metres, m/s, m/s²)</option>
              <option value="imperial">Imperial (feet, ft/s)</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 mb-1">PLANNER COORDINATE CONVENTION:</label>
            <input
              type="text"
              disabled
              value="ENU_ALT_UP (X:East, Y:North, Z:Altitude Positive Up)"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-400"
            />
          </div>
        </div>
      </Card>
    </div>
  )
}
