import { controlClient } from './axiosClient'
import { MissionAnalyticsSummary, ExperimentTrial } from '../types/analytics'
import { MOCK_ANALYTICS_SUMMARY, MOCK_EXPERIMENT_TRIALS } from '../mock/mockAnalytics'

export const analyticsApi = {
  async getMissionAnalytics(
    missionId: string,
    isDemoMode: boolean = true
  ): Promise<MissionAnalyticsSummary> {
    if (isDemoMode) {
      return {
        ...MOCK_ANALYTICS_SUMMARY,
        mission_id: missionId,
      }
    }
    const response = await controlClient.get<MissionAnalyticsSummary>(`/api/analytics/mission/${missionId}`)
    return response.data
  },

  async getExperimentTrials(isDemoMode: boolean = true): Promise<ExperimentTrial[]> {
    if (isDemoMode) {
      return MOCK_EXPERIMENT_TRIALS
    }
    const response = await controlClient.get<ExperimentTrial[]>('/api/analytics/experiments')
    return response.data
  },
}
