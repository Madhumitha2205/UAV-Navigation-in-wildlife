export function formatDistance(metres: number | undefined | null): string {
  if (metres === undefined || metres === null || isNaN(metres)) return '-- m'
  if (metres >= 1000) {
    return `${(metres / 1000).toFixed(2)} km`
  }
  return `${metres.toFixed(1)} m`
}

export function formatSpeed(mps: number | undefined | null): string {
  if (mps === undefined || mps === null || isNaN(mps)) return '-- m/s'
  return `${mps.toFixed(2)} m/s`
}

export function formatAltitude(metres: number | undefined | null): string {
  if (metres === undefined || metres === null || isNaN(metres)) return '-- m'
  return `${metres.toFixed(1)} m`
}

export function formatPercentage(val: number | undefined | null): string {
  if (val === undefined || val === null || isNaN(val)) return '--%'
  return `${Math.round(val)}%`
}

export function formatCoord(val: number | undefined | null): string {
  if (val === undefined || val === null || isNaN(val)) return '0.00'
  return val.toFixed(2)
}

export function formatDuration(seconds: number | undefined | null): string {
  if (seconds === undefined || seconds === null || isNaN(seconds)) return '--s'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  if (mins > 0) {
    return `${mins}m ${secs}s`
  }
  return `${seconds.toFixed(1)}s`
}

export function formatTimestamp(time: number | string | Date): string {
  try {
    const d = new Date(time)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return String(time)
  }
}
