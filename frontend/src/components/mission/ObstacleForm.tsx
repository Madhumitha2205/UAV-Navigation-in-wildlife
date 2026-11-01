import React, { useState } from 'react'
import { Plus, Trash2, AlertTriangle, Circle, Square } from 'lucide-react'
import { StaticObstacle } from '../../types/environment'
import { Card } from '../common/Card'
import { Button } from '../common/Button'
import { Badge } from '../common/Badge'

export interface ObstacleFormProps {
  obstacles: StaticObstacle[]
  onAddObstacle: (obs: StaticObstacle) => void
  onRemoveObstacle: (id: string) => void
}

export const ObstacleForm: React.FC<ObstacleFormProps> = ({
  obstacles,
  onAddObstacle,
  onRemoveObstacle,
}) => {
  const [obsType, setObsType] = useState<'circle' | 'rectangle'>('circle')
  const [obsId, setObsId] = useState(`OBS_${obstacles.length + 1}`)
  const [cx, setCx] = useState(25)
  const [cy, setCy] = useState(20)
  const [cz, setCz] = useState(16)
  const [radius, setRadius] = useState(3.0)

  // Rectangular fields
  const [minX, setMinX] = useState(20)
  const [minY, setMinY] = useState(30)
  const [maxX, setMaxX] = useState(28)
  const [maxY, setMaxY] = useState(38)

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!obsId.trim()) return

    if (obsType === 'circle') {
      onAddObstacle({
        id: obsId.trim(),
        type: 'circle',
        x: Number(cx),
        y: Number(cy),
        z: Number(cz),
        radius: Number(radius),
      })
    } else {
      onAddObstacle({
        id: obsId.trim(),
        type: 'rectangle',
        min_x: Number(minX),
        min_y: Number(minY),
        max_x: Number(maxX),
        max_y: Number(maxY),
        z: Number(cz),
      })
    }
    setObsId(`OBS_${obstacles.length + 2}`)
  }

  return (
    <Card
      title={`Geometric Hazards & Static Obstacles (${obstacles.length})`}
      subtitle="Forest trees, towers, ridges, and canopy collision zones"
      icon={<AlertTriangle className="w-4 h-4 text-rose-400" />}
    >
      <div className="space-y-4">
        {/* Obstacle Table */}
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-900/80 text-slate-400 font-mono border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Hazard ID</th>
                <th className="py-2.5 px-3">Geometry</th>
                <th className="py-2.5 px-3">Position / Extents</th>
                <th className="py-2.5 px-3">Dimensions</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {obstacles.map((obs) => (
                <tr key={obs.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-2.5 px-3 font-semibold text-rose-400">{obs.id}</td>
                  <td className="py-2.5 px-3">
                    <Badge variant="danger" className="text-[10px] gap-1">
                      {obs.type === 'circle' ? <Circle className="w-2.5 h-2.5" /> : <Square className="w-2.5 h-2.5" />}
                      {obs.type.toUpperCase()}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3 text-slate-300">
                    {obs.type === 'circle'
                      ? `Center: (${obs.x.toFixed(1)}, ${obs.y.toFixed(1)})`
                      : `[${obs.min_x}, ${obs.min_y}] to [${obs.max_x}, ${obs.max_y}]`}
                  </td>
                  <td className="py-2.5 px-3 text-slate-400">
                    {obs.type === 'circle' ? `Radius: ${obs.radius.toFixed(1)}m` : `Area: ${(obs.max_x - obs.min_x) * (obs.max_y - obs.min_y)}m²`}
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <button
                      onClick={() => onRemoveObstacle(obs.id)}
                      className="p-1 text-slate-400 hover:text-rose-400"
                      title="Remove Obstacle"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Add Obstacle Form */}
        <form onSubmit={handleCreate} className="bg-slate-900/60 border border-slate-800 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-slate-300 font-mono">
              + ADD STATIC HAZARD
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setObsType('circle')}
                className={`px-2 py-0.5 rounded text-[11px] font-mono border ${
                  obsType === 'circle' ? 'bg-rose-950 border-rose-600 text-rose-300' : 'bg-slate-800 border-slate-700 text-slate-400'
                }`}
              >
                Circular
              </button>
              <button
                type="button"
                onClick={() => setObsType('rectangle')}
                className={`px-2 py-0.5 rounded text-[11px] font-mono border ${
                  obsType === 'rectangle' ? 'bg-rose-950 border-rose-600 text-rose-300' : 'bg-slate-800 border-slate-700 text-slate-400'
                }`}
              >
                Rectangular
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-6 gap-2 text-xs">
            <input
              type="text"
              placeholder="Hazard ID"
              value={obsId}
              onChange={(e) => setObsId(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono"
            />

            {obsType === 'circle' ? (
              <>
                <input
                  type="number"
                  placeholder="Center X"
                  value={cx}
                  onChange={(e) => setCx(parseFloat(e.target.value) || 0)}
                  className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono text-center"
                />
                <input
                  type="number"
                  placeholder="Center Y"
                  value={cy}
                  onChange={(e) => setCy(parseFloat(e.target.value) || 0)}
                  className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono text-center"
                />
                <input
                  type="number"
                  placeholder="Radius (m)"
                  step="0.5"
                  value={radius}
                  onChange={(e) => setRadius(parseFloat(e.target.value) || 1)}
                  className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono text-center"
                />
                <input
                  type="number"
                  placeholder="Alt Z"
                  value={cz}
                  onChange={(e) => setCz(parseFloat(e.target.value) || 15)}
                  className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono text-center"
                />
              </>
            ) : (
              <>
                <input
                  type="number"
                  placeholder="Min X"
                  value={minX}
                  onChange={(e) => setMinX(parseFloat(e.target.value) || 0)}
                  className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono text-center"
                />
                <input
                  type="number"
                  placeholder="Min Y"
                  value={minY}
                  onChange={(e) => setMinY(parseFloat(e.target.value) || 0)}
                  className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono text-center"
                />
                <input
                  type="number"
                  placeholder="Max X"
                  value={maxX}
                  onChange={(e) => setMaxX(parseFloat(e.target.value) || 0)}
                  className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono text-center"
                />
                <input
                  type="number"
                  placeholder="Max Y"
                  value={maxY}
                  onChange={(e) => setMaxY(parseFloat(e.target.value) || 0)}
                  className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono text-center"
                />
              </>
            )}

            <Button type="submit" variant="danger" size="sm" className="h-full">
              <Plus className="w-3.5 h-3.5 mr-1" />
              Add Hazard
            </Button>
          </div>
        </form>
      </div>
    </Card>
  )
}
