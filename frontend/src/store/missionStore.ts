import { create } from 'zustand'
import { EnvironmentConfig, MonitoringWaypoint, StaticObstacle, GAPlanningParameters } from '../types/environment'
import { GlobalRoutePlan } from '../types/route'
import { ActivityEvent } from '../types/mission'
import { DEFAULT_ENVIRONMENT_CONFIG, MOCK_GLOBAL_ROUTE } from '../mock/mockRoute'
import { globalPlannerApi } from '../api/globalPlannerApi'
import { useSettingsStore } from './settingsStore'

interface MissionState {
  environmentConfig: EnvironmentConfig
  currentRoutePlan: GlobalRoutePlan | null
  isPlanning: boolean
  planningError: string | null
  recentActivities: ActivityEvent[]

  // Actions
  updateEnvironment: (partial: Partial<EnvironmentConfig>) => void
  addWaypoint: (waypoint: MonitoringWaypoint) => void
  updateWaypoint: (id: string, updated: Partial<MonitoringWaypoint>) => void
  removeWaypoint: (id: string) => void
  addObstacle: (obstacle: StaticObstacle) => void
  removeObstacle: (id: string) => void
  updatePlanningParams: (params: Partial<GAPlanningParameters>) => void
  planRoute: () => Promise<void>
  resetToDefaults: () => void
  addActivity: (event: Omit<ActivityEvent, 'id' | 'timestamp'>) => void
}

const initialActivities: ActivityEvent[] = [
  {
    id: 'ACT_1',
    timestamp: '11:30:12',
    title: 'Mission Initialized',
    description: 'Wildlife corridor survey configuration loaded',
    category: 'MISSION',
    severity: 'info',
  },
  {
    id: 'ACT_2',
    timestamp: '11:31:05',
    title: 'Route Generated',
    description: 'GA + 2-Opt + A* route completed with 100% monitoring coverage',
    category: 'PLANNER',
    severity: 'success',
  },
  {
    id: 'ACT_3',
    timestamp: '11:32:40',
    title: 'AirSim Simulation Ready',
    description: 'Multirotor PX4 state aligned to ENU origin [DEMO]',
    category: 'SIMULATION',
    severity: 'info',
  },
]

export const useMissionStore = create<MissionState>((set, get) => ({
  environmentConfig: DEFAULT_ENVIRONMENT_CONFIG,
  currentRoutePlan: MOCK_GLOBAL_ROUTE,
  isPlanning: false,
  planningError: null,
  recentActivities: initialActivities,

  updateEnvironment: (partial) =>
    set((state) => ({
      environmentConfig: { ...state.environmentConfig, ...partial },
    })),

  addWaypoint: (waypoint) =>
    set((state) => ({
      environmentConfig: {
        ...state.environmentConfig,
        monitoring_waypoints: [...state.environmentConfig.monitoring_waypoints, waypoint],
      },
    })),

  updateWaypoint: (id, updated) =>
    set((state) => ({
      environmentConfig: {
        ...state.environmentConfig,
        monitoring_waypoints: state.environmentConfig.monitoring_waypoints.map((wp) =>
          wp.id === id ? { ...wp, ...updated } : wp
        ),
      },
    })),

  removeWaypoint: (id) =>
    set((state) => ({
      environmentConfig: {
        ...state.environmentConfig,
        monitoring_waypoints: state.environmentConfig.monitoring_waypoints.filter((wp) => wp.id !== id),
      },
    })),

  addObstacle: (obstacle) =>
    set((state) => ({
      environmentConfig: {
        ...state.environmentConfig,
        obstacles: [...state.environmentConfig.obstacles, obstacle],
      },
    })),

  removeObstacle: (id) =>
    set((state) => ({
      environmentConfig: {
        ...state.environmentConfig,
        obstacles: state.environmentConfig.obstacles.filter((obs) => obs.id !== id),
      },
    })),

  updatePlanningParams: (params) =>
    set((state) => ({
      environmentConfig: {
        ...state.environmentConfig,
        planning_params: { ...state.environmentConfig.planning_params, ...params },
      },
    })),

  planRoute: async () => {
    const isDemo = useSettingsStore.getState().demoMode
    set({ isPlanning: true, planningError: null })

    try {
      const result = await globalPlannerApi.planRoute(get().environmentConfig, isDemo)
      set({
        currentRoutePlan: result.route,
        isPlanning: false,
      })
      get().addActivity({
        title: result.is_demo ? 'Route Generated [DEMO]' : 'Route Generated (Live GA Planner)',
        description: `Path length: ${result.route.path_metrics.planned_path_length_m}m with ${result.route.monitoring_waypoints.length} waypoints`,
        category: 'PLANNER',
        severity: 'success',
      })
    } catch (err: any) {
      const msg = err.response?.data?.message || err.message || 'Route planning failed'
      set({ isPlanning: false, planningError: msg })
      get().addActivity({
        title: 'Route Planning Failed',
        description: msg,
        category: 'PLANNER',
        severity: 'danger',
      })
    }
  },

  resetToDefaults: () =>
    set({
      environmentConfig: DEFAULT_ENVIRONMENT_CONFIG,
      currentRoutePlan: MOCK_GLOBAL_ROUTE,
      planningError: null,
    }),

  addActivity: (event) =>
    set((state) => {
      const newEvent: ActivityEvent = {
        ...event,
        id: `ACT_${Date.now()}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      }
      return {
        recentActivities: [newEvent, ...state.recentActivities.slice(0, 19)], // keep last 20
      }
    }),
}))
