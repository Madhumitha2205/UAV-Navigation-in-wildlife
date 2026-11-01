import axios from 'axios'

// Configurable environment URLs with fallback
export const GLOBAL_API_URL = import.meta.env.VITE_GLOBAL_API_URL || 'http://localhost:8000'
export const CONTROL_API_URL = import.meta.env.VITE_CONTROL_API_URL || 'http://localhost:8001'
export const DEFAULT_WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws/telemetry'

export const globalPlannerClient = axios.create({
  baseURL: GLOBAL_API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const controlClient = axios.create({
  baseURL: CONTROL_API_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})
