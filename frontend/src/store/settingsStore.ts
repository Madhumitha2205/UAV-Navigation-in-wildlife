import { create } from 'zustand'

interface SettingsState {
  demoMode: boolean
  globalApiUrl: string
  controlApiUrl: string
  wsUrl: string
  units: 'metric' | 'imperial'
  theme: 'dark' | 'light'
  setDemoMode: (enabled: boolean) => void
  setGlobalApiUrl: (url: string) => void
  setControlApiUrl: (url: string) => void
  setWsUrl: (url: string) => void
  setUnits: (units: 'metric' | 'imperial') => void
  setTheme: (theme: 'dark' | 'light') => void
  resetDefaults: () => void
}

const defaultGlobalApi = import.meta.env.VITE_GLOBAL_API_URL || 'http://localhost:8000'
const defaultControlApi = import.meta.env.VITE_CONTROL_API_URL || 'http://localhost:8001'
const defaultWsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws/telemetry'
const defaultDemoMode = import.meta.env.VITE_DEMO_MODE !== 'false'

export const useSettingsStore = create<SettingsState>((set) => ({
  demoMode: defaultDemoMode,
  globalApiUrl: defaultGlobalApi,
  controlApiUrl: defaultControlApi,
  wsUrl: defaultWsUrl,
  units: 'metric',
  theme: 'dark',

  setDemoMode: (enabled) => set({ demoMode: enabled }),
  setGlobalApiUrl: (url) => set({ globalApiUrl: url }),
  setControlApiUrl: (url) => set({ controlApiUrl: url }),
  setWsUrl: (url) => set({ wsUrl: url }),
  setUnits: (units) => set({ units }),
  setTheme: (theme) => set({ theme }),
  resetDefaults: () =>
    set({
      demoMode: true,
      globalApiUrl: defaultGlobalApi,
      controlApiUrl: defaultControlApi,
      wsUrl: defaultWsUrl,
      units: 'metric',
      theme: 'dark',
    }),
}))
