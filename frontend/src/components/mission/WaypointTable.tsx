import React, { useState } from 'react'
import { Plus, Trash2, Edit2, Check, X, MapPin } from 'lucide-react'
import { MonitoringWaypoint } from '../../types/environment'
import { Card } from '../common/Card'
import { Button } from '../common/Button'
import { Badge } from '../common/Badge'

export interface WaypointTableProps {
  waypoints: MonitoringWaypoint[]
  onAddWaypoint: (wp: MonitoringWaypoint) => void
  onUpdateWaypoint: (id: string, updated: Partial<MonitoringWaypoint>) => void
  onRemoveWaypoint: (id: string) => void
}

export const WaypointTable: React.FC<WaypointTableProps> = ({
  waypoints,
  onAddWaypoint,
  onUpdateWaypoint,
  onRemoveWaypoint,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<Partial<MonitoringWaypoint>>({})

  // New waypoint form state
  const [newId, setNewId] = useState(`WP_${waypoints.length + 1}`)
  const [newZone, setNewZone] = useState('Wildlife_Corridor')
  const [newX, setNewX] = useState(30)
  const [newY, setNewY] = useState(25)
  const [newZ, setNewZ] = useState(16)
  const [newPriority, setNewPriority] = useState(1)

  const handleStartEdit = (wp: MonitoringWaypoint) => {
    setEditingId(wp.id)
    setEditForm({ ...wp })
  }

  const handleSaveEdit = (id: string) => {
    onUpdateWaypoint(id, editForm)
    setEditingId(null)
  }

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newId.trim() || !newZone.trim()) return

    onAddWaypoint({
      id: newId.trim(),
      zone_name: newZone.trim(),
      x: Number(newX),
      y: Number(newY),
      z: Number(newZ),
      priority: Number(newPriority),
    })

    setNewId(`WP_${waypoints.length + 2}`)
  }

  return (
    <Card
      title={`Configured Wildlife Monitoring Waypoints (${waypoints.length})`}
      subtitle="Targets visited by global GA planner with TSP 2-Opt sequencing"
      icon={<MapPin className="w-4 h-4 text-cyan-400" />}
    >
      <div className="space-y-4">
        {/* Waypoints List Table */}
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-900/80 text-slate-400 font-mono border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">ID</th>
                <th className="py-2.5 px-3">Zone / Habitat</th>
                <th className="py-2.5 px-3">Coords (X, Y, Z)</th>
                <th className="py-2.5 px-3">Priority</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {waypoints.map((wp) => {
                const isEditing = editingId === wp.id

                return (
                  <tr key={wp.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-2.5 px-3 font-semibold text-cyan-400">{wp.id}</td>

                    <td className="py-2.5 px-3 font-sans">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editForm.zone_name || ''}
                          onChange={(e) => setEditForm({ ...editForm, zone_name: e.target.value })}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-100"
                        />
                      ) : (
                        wp.zone_name
                      )}
                    </td>

                    <td className="py-2.5 px-3 text-slate-300">
                      {isEditing ? (
                        <div className="flex gap-1">
                          <input
                            type="number"
                            value={editForm.x ?? wp.x}
                            onChange={(e) => setEditForm({ ...editForm, x: parseFloat(e.target.value) || 0 })}
                            className="w-14 bg-slate-900 border border-slate-700 rounded px-1 py-1"
                          />
                          <input
                            type="number"
                            value={editForm.y ?? wp.y}
                            onChange={(e) => setEditForm({ ...editForm, y: parseFloat(e.target.value) || 0 })}
                            className="w-14 bg-slate-900 border border-slate-700 rounded px-1 py-1"
                          />
                          <input
                            type="number"
                            value={editForm.z ?? wp.z}
                            onChange={(e) => setEditForm({ ...editForm, z: parseFloat(e.target.value) || 0 })}
                            className="w-14 bg-slate-900 border border-slate-700 rounded px-1 py-1"
                          />
                        </div>
                      ) : (
                        `[${wp.x.toFixed(1)}, ${wp.y.toFixed(1)}, ${wp.z.toFixed(1)}]`
                      )}
                    </td>

                    <td className="py-2.5 px-3">
                      <Badge
                        variant={wp.priority === 1 ? 'danger' : wp.priority === 2 ? 'warning' : 'primary'}
                        className="text-[10px]"
                      >
                        {wp.priority === 1 ? 'High (P1)' : wp.priority === 2 ? 'Med (P2)' : 'Low (P3)'}
                      </Badge>
                    </td>

                    <td className="py-2.5 px-3 text-right">
                      {isEditing ? (
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => handleSaveEdit(wp.id)}
                            className="p-1 text-emerald-400 hover:text-emerald-300"
                            title="Save"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="p-1 text-slate-400 hover:text-white"
                            title="Cancel"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => handleStartEdit(wp)}
                            className="p-1 text-slate-400 hover:text-sky-400"
                            title="Edit"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => onRemoveWaypoint(wp.id)}
                            className="p-1 text-slate-400 hover:text-rose-400"
                            title="Delete"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Add Waypoint Form */}
        <form onSubmit={handleCreate} className="bg-slate-900/60 border border-slate-800 rounded-lg p-3">
          <span className="text-[11px] font-semibold text-slate-300 block mb-2 font-mono">
            + ADD MONITORING WAYPOINT
          </span>
          <div className="grid grid-cols-2 md:grid-cols-6 gap-2 text-xs">
            <input
              type="text"
              placeholder="ID"
              value={newId}
              onChange={(e) => setNewId(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono"
            />
            <input
              type="text"
              placeholder="Zone Name"
              value={newZone}
              onChange={(e) => setNewZone(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100"
            />
            <input
              type="number"
              placeholder="X"
              value={newX}
              onChange={(e) => setNewX(parseFloat(e.target.value) || 0)}
              className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono text-center"
            />
            <input
              type="number"
              placeholder="Y"
              value={newY}
              onChange={(e) => setNewY(parseFloat(e.target.value) || 0)}
              className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono text-center"
            />
            <input
              type="number"
              placeholder="Z"
              value={newZ}
              onChange={(e) => setNewZ(parseFloat(e.target.value) || 0)}
              className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono text-center"
            />
            <Button type="submit" variant="primary" size="sm" className="h-full">
              <Plus className="w-3.5 h-3.5 mr-1" />
              Add
            </Button>
          </div>
        </form>
      </div>
    </Card>
  )
}
