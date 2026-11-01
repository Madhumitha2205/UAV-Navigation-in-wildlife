import React from 'react'
import { Cpu, RotateCcw, Play } from 'lucide-react'
import { GAPlanningParameters } from '../../types/environment'
import { Card } from '../common/Card'
import { Button } from '../common/Button'

export interface PlanningParamsFormProps {
  params: GAPlanningParameters
  onChange: (updated: Partial<GAPlanningParameters>) => void
  onResetDefaults: () => void
  onGenerateRoute: () => void
  isPlanning: boolean
}

export const PlanningParamsForm: React.FC<PlanningParamsFormProps> = ({
  params,
  onChange,
  onResetDefaults,
  onGenerateRoute,
  isPlanning,
}) => {
  return (
    <Card
      title="Global Planner Parameters (GA + 2-Opt + A*)"
      subtitle="Evolutionary optimization hyperparameters and local search heuristics"
      icon={<Cpu className="w-4 h-4 text-purple-400" />}
      action={
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onResetDefaults} disabled={isPlanning}>
            <RotateCcw className="w-3.5 h-3.5 mr-1" />
            Restore Defaults
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={onGenerateRoute}
            isLoading={isPlanning}
            className="shadow-lg shadow-sky-900/40"
          >
            <Play className="w-3.5 h-3.5 mr-1" />
            Generate Route
          </Button>
        </div>
      }
    >
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3 text-xs">
        <div>
          <label className="block text-slate-400 mb-1">Pop Size</label>
          <input
            type="number"
            value={params.population_size}
            onChange={(e) => onChange({ population_size: parseInt(e.target.value) || 10 })}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-slate-400 mb-1">Max Gens</label>
          <input
            type="number"
            value={params.max_generations}
            onChange={(e) => onChange({ max_generations: parseInt(e.target.value) || 5 })}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-slate-400 mb-1">Crossover P</label>
          <input
            type="number"
            step="0.05"
            min="0"
            max="1"
            value={params.crossover_probability}
            onChange={(e) => onChange({ crossover_probability: parseFloat(e.target.value) || 0.8 })}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-slate-400 mb-1">Mutation P</label>
          <input
            type="number"
            step="0.05"
            min="0"
            max="1"
            value={params.mutation_probability}
            onChange={(e) => onChange({ mutation_probability: parseFloat(e.target.value) || 0.1 })}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-slate-400 mb-1">2-Opt Freq</label>
          <input
            type="number"
            value={params.two_opt_frequency}
            onChange={(e) => onChange({ two_opt_frequency: parseInt(e.target.value) || 1 })}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-slate-400 mb-1">2-Opt Pop %</label>
          <input
            type="number"
            value={params.two_opt_population_pct}
            onChange={(e) => onChange({ two_opt_population_pct: parseFloat(e.target.value) || 0 })}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-slate-400 mb-1">Random Seed</label>
          <input
            type="number"
            value={params.random_seed ?? 42}
            onChange={(e) => onChange({ random_seed: parseInt(e.target.value) || undefined })}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
          />
        </div>
      </div>
    </Card>
  )
}
