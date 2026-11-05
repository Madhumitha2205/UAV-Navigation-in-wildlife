export interface GeoCoordinate {
  lat: number
  lon: number
  alt?: number
  name?: string
  description?: string
}

export const INDIAN_WILDLIFE_RESERVES: GeoCoordinate[] = [
  {
    name: 'Kaziranga National Park',
    description: 'Assam - Rhino & Elephant Corridor',
    lat: 26.5775,
    lon: 93.1711,
    alt: 12.0,
  },
  {
    name: 'Jim Corbett National Park',
    description: 'Uttarakhand - Tiger Reserve & Foothills',
    lat: 29.5300,
    lon: 78.7747,
    alt: 15.0,
  },
  {
    name: 'Bandipur National Park',
    description: 'Karnataka - Western Ghats Wildlife Sanctuary',
    lat: 11.6664,
    lon: 76.6291,
    alt: 14.0,
  },
  {
    name: 'Ranthambore National Park',
    description: 'Rajasthan - Dry Deciduous Tiger Forest',
    lat: 26.0173,
    lon: 76.5026,
    alt: 12.0,
  },
  {
    name: 'Gir National Park',
    description: 'Gujarat - Asiatic Lion Sanctuary',
    lat: 21.1243,
    lon: 70.8242,
    alt: 10.0,
  },
  {
    name: 'Sundarbans National Park',
    description: 'West Bengal - Mangrove Tiger Reserve',
    lat: 21.9497,
    lon: 88.8999,
    alt: 8.0,
  },
  {
    name: 'Periyar National Park',
    description: 'Kerala - Cardamom Hills Elephant Sanctuary',
    lat: 9.4679,
    lon: 77.1435,
    alt: 15.0,
  },
  {
    name: 'Kanha Tiger Reserve',
    description: 'Madhya Pradesh - Sal and Bamboo Forest',
    lat: 22.3345,
    lon: 80.6115,
    alt: 12.0,
  },
  {
    name: 'Mudumalai Wildlife Sanctuary',
    description: 'Tamil Nadu - Nilgiri Biosphere Corridor',
    lat: 11.5623,
    lon: 76.5341,
    alt: 14.0,
  },
  {
    name: 'Nagarhole National Park',
    description: 'Karnataka - Kabini River Corridor',
    lat: 12.0314,
    lon: 76.1207,
    alt: 12.0,
  },
  {
    name: 'Tadoba Andhari Tiger Reserve',
    description: 'Maharashtra - Chandrapur Wildlife Basin',
    lat: 20.2529,
    lon: 79.3038,
    alt: 10.0,
  },
  {
    name: 'Hemis National Park',
    description: 'Ladakh - High Altitude Snow Leopard Habitat',
    lat: 33.9167,
    lon: 77.4167,
    alt: 25.0,
  },
  {
    name: 'New Delhi (HQ)',
    description: 'National Capital Territory',
    lat: 28.6139,
    lon: 77.2090,
    alt: 10.0,
  },
  {
    name: 'Bengaluru Flight Lab',
    description: 'Karnataka Aerospace Corridor',
    lat: 12.9716,
    lon: 77.5946,
    alt: 10.0,
  },
  {
    name: 'Mumbai Coastal Node',
    description: 'Maharashtra Western Node',
    lat: 19.0760,
    lon: 72.8777,
    alt: 10.0,
  },
]

export const INDIA_MAP_BOUNDS: [[number, number], [number, number]] = [
  [6.5, 68.0], // South-West
  [37.5, 97.5], // North-East
]

export const INDIA_CENTER_COORDINATES: [number, number] = [20.5937, 78.9629]

/**
 * Calculates great-circle Haversine distance in metres between two GPS points.
 */
export function haversineDistanceM(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371000 // Earth radius in metres
  const phi1 = (lat1 * Math.PI) / 180
  const phi2 = (lat2 * Math.PI) / 180
  const deltaPhi = ((lat2 - lat1) * Math.PI) / 180
  const deltaLambda = ((lon2 - lon1) * Math.PI) / 180

  const a =
    Math.sin(deltaPhi / 2) * Math.sin(deltaPhi / 2) +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2) * Math.sin(deltaLambda / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))

  return R * c
}

/**
 * Calculates compass heading bearing in degrees [0, 360).
 */
export function calculateBearingDeg(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const phi1 = (lat1 * Math.PI) / 180
  const phi2 = (lat2 * Math.PI) / 180
  const lambda1 = (lon1 * Math.PI) / 180
  const lambda2 = (lon2 * Math.PI) / 180

  const y = Math.sin(lambda2 - lambda1) * Math.cos(phi2)
  const x =
    Math.cos(phi1) * Math.sin(phi2) -
    Math.sin(phi1) * Math.cos(phi2) * Math.cos(lambda2 - lambda1)
  const theta = Math.atan2(y, x)
  return ((theta * 180) / Math.PI + 360) % 360
}

/**
 * Converts a Local ENU coordinate (x, y, z) into GPS coordinates relative to origin.
 */
export function enuToGps(
  x_m: number,
  y_m: number,
  originLat: number,
  originLon: number,
  scaleFactor = 1.0
): { lat: number; lon: number } {
  const metresPerDegLat = 111320.0
  const metresPerDegLon = 111320.0 * Math.cos((originLat * Math.PI) / 180.0)

  const rawEast = x_m / scaleFactor
  const rawNorth = y_m / scaleFactor

  const dLat = rawNorth / metresPerDegLat
  const dLon = rawEast / (metresPerDegLon || 1e-4)

  return {
    lat: Number((originLat + dLat).toFixed(6)),
    lon: Number((originLon + dLon).toFixed(6)),
  }
}
