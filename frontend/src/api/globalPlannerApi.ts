import { globalPlannerClient } from './axiosClient'
import { EnvironmentConfig } from '../types/environment'
import { GlobalRoutePlan } from '../types/route'
import { MOCK_GLOBAL_ROUTE } from '../mock/mockRoute'

export interface PlanRouteResponse {
  route: GlobalRoutePlan
  is_demo: boolean
}

export const globalPlannerApi = {
  async planRoute(
    config: EnvironmentConfig,
    isDemoMode: boolean = true
  ): Promise<PlanRouteResponse> {
    if (isDemoMode) {
      // Simulate planner calculation latency
      await new Promise((resolve) => setTimeout(resolve, 800))
      
      // Adapt mock route based on custom waypoints if configured
      const adaptedRoute: GlobalRoutePlan = {
        ...MOCK_GLOBAL_ROUTE,
        mission_id: `mission_wildlife_${Date.now().toString(36)}`,
        start_position: config.start_position,
        destination: config.destination,
        monitoring_waypoints: config.monitoring_waypoints,
        static_obstacles: config.obstacles,
        path_metrics: {
          ...MOCK_GLOBAL_ROUTE.path_metrics,
          num_monitoring_waypoints: config.monitoring_waypoints.length,
        },
      }
      return { route: adaptedRoute, is_demo: true }
    }

    const response = await globalPlannerClient.post<GlobalRoutePlan>('/api/planner/plan', config)
    return { route: response.data, is_demo: false }
  },

  async getRoute(routeId: string, isDemoMode: boolean = true): Promise<PlanRouteResponse> {
    if (isDemoMode) {
      return { route: MOCK_GLOBAL_ROUTE, is_demo: true }
    }
    const response = await globalPlannerClient.get<GlobalRoutePlan>(`/api/planner/route/${routeId}`)
    return { route: response.data, is_demo: false }
  },

  async getPlannerStatus(jobId: string, isDemoMode: boolean = true) {
    if (isDemoMode) {
      return { job_id: jobId, status: 'SUCCESS', progress_pct: 100 }
    }
    const response = await globalPlannerClient.get(`/api/planner/status/${jobId}`)
    return response.data
  },
}
