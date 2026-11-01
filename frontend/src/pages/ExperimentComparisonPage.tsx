import React from 'react'
import { GitCompare, FileSpreadsheet } from 'lucide-react'
import { ExperimentComparison } from '../components/analytics/ExperimentComparison'
import { MOCK_EXPERIMENT_TRIALS } from '../mock/mockAnalytics'
import { Badge } from '../components/common/Badge'

export const ExperimentComparisonPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-[#0c1424] border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-slate-100 tracking-wide flex items-center gap-2">
              <GitCompare className="w-5 h-5 text-sky-400" />
              EXPERIMENTAL FRAMEWORK COMPARISON
            </h1>
            <Badge variant="primary">3 CONFIGURATIONS</Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Comparative evaluation across Configuration A (Baseline), Configuration B (TD3 Raw), and Configuration C (Proposed Hierarchical TD3 + AFL)
          </p>
        </div>

        <div className="text-xs font-mono text-slate-400">
          <span>SOURCE:</span>{' '}
          <span className="text-slate-200">logs/evaluation_summary.csv</span>
        </div>
      </div>

      {/* Comparative Evaluation Matrix & Chart */}
      <ExperimentComparison trials={MOCK_EXPERIMENT_TRIALS} />
    </div>
  )
}
