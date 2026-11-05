import React, { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import {
  Compass,
  MapPin,
  Flag,
  RotateCcw,
  Search,
  Crosshair,
  Layers,
  ZoomIn,
  ZoomOut,
  Navigation,
  AlertTriangle,
} from 'lucide-react'
import {
  GeoCoordinate,
  INDIAN_WILDLIFE_RESERVES,
  INDIA_CENTER_COORDINATES,
  haversineDistanceM,
} from '../../utils/geoUtils'
import { GlobalRoutePlan } from '../../types/route'
import { TelemetryPacket } from '../../types/telemetry'

export interface IndiaLeafletMapProps {
  routePlan?: GlobalRoutePlan | null
  telemetry?: TelemetryPacket | null
  startPoint: GeoCoordinate
  destination: GeoCoordinate
  waypoints: GeoCoordinate[]
  onStartChange?: (coord: GeoCoordinate) => void
  onDestinationChange?: (coord: GeoCoordinate) => void
  onWaypointAdd?: (coord: GeoCoordinate) => void
  onWaypointUpdate?: (index: number, coord: GeoCoordinate) => void
  onWaypointRemove?: (index: number) => void
  interactive?: boolean
  height?: number | string
  actualTrajectory?: { lat: number; lon: number }[]
  mode?: 'SELECT_START' | 'SELECT_DEST' | 'ADD_WAYPOINT' | 'VIEW'
  onModeChange?: (mode: 'SELECT_START' | 'SELECT_DEST' | 'ADD_WAYPOINT' | 'VIEW') => void
}

// Fix Leaflet Default Icon path issues
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

// Custom HTML Markers
function createDivIcon(html: string, className = '', iconSize: [number, number] = [28, 28]) {
  return L.divIcon({
    html,
    className: `custom-div-icon ${className}`,
    iconSize,
    iconAnchor: [iconSize[0] / 2, iconSize[1] / 2],
    popupAnchor: [0, -iconSize[1] / 2],
  })
}

export const IndiaLeafletMap: React.FC<IndiaLeafletMapProps> = ({
  routePlan,
  telemetry,
  startPoint,
  destination,
  waypoints,
  onStartChange,
  onDestinationChange,
  onWaypointAdd,
  onWaypointUpdate,
  interactive = true,
  height = 560,
  actualTrajectory = [],
  mode = 'ADD_WAYPOINT',
  onModeChange,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const markersLayerRef = useRef<L.LayerGroup | null>(null)
  const routesLayerRef = useRef<L.LayerGroup | null>(null)
  const uavMarkerRef = useRef<L.Marker | null>(null)

  const [activeTileLayer, setActiveTileLayer] = useState<'DARK' | 'OSM'>('DARK')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<GeoCoordinate[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [activeMode, setActiveMode] = useState<'SELECT_START' | 'SELECT_DEST' | 'ADD_WAYPOINT' | 'VIEW'>(mode)

  // Sync mode with parent
  useEffect(() => {
    setActiveMode(mode)
  }, [mode])

  const handleModeChange = (newMode: 'SELECT_START' | 'SELECT_DEST' | 'ADD_WAYPOINT' | 'VIEW') => {
    setActiveMode(newMode)
    if (onModeChange) onModeChange(newMode)
  }

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return
    if (mapInstanceRef.current) return

    const initialCenter: [number, number] = [startPoint.lat || 20.5937, startPoint.lon || 78.9629]

    const map = L.map(mapContainerRef.current, {
      center: initialCenter,
      zoom: 6,
      minZoom: 4,
      maxZoom: 18,
      zoomControl: false, // Custom styled zoom controls
      attributionControl: false,
    })

    // CartoDB Dark Matter for HUD feel
    const darkTiles = L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      {
        subdomains: 'abcd',
        maxZoom: 19,
      }
    )

    // Standard OpenStreetMap
    const osmTiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
    })

    if (activeTileLayer === 'DARK') {
      darkTiles.addTo(map)
    } else {
      osmTiles.addTo(map)
    }

    (map as any)._darkTiles = darkTiles;
    (map as any)._osmTiles = osmTiles

    const markersLayer = L.layerGroup().addTo(map)
    const routesLayer = L.layerGroup().addTo(map)

    markersLayerRef.current = markersLayer
    routesLayerRef.current = routesLayer
    mapInstanceRef.current = map

    // Handle Map Clicks for Waypoint/Start/Destination Selection
    map.on('click', (e: L.LeafletMouseEvent) => {
      if (!interactive) return
      const clickedCoord: GeoCoordinate = {
        lat: Number(e.latlng.lat.toFixed(6)),
        lon: Number(e.latlng.lng.toFixed(6)),
        alt: 12.0,
      }

      if (activeMode === 'SELECT_START') {
        if (onStartChange) onStartChange(clickedCoord)
        handleModeChange('ADD_WAYPOINT')
      } else if (activeMode === 'SELECT_DEST') {
        if (onDestinationChange) onDestinationChange(clickedCoord)
        handleModeChange('ADD_WAYPOINT')
      } else if (activeMode === 'ADD_WAYPOINT') {
        if (onWaypointAdd) onWaypointAdd(clickedCoord)
      }
    })

    return () => {
      map.remove()
      mapInstanceRef.current = null
    }
  }, [])

  // Toggle Tile Layer
  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map) return
    const darkTiles = (map as any)._darkTiles
    const osmTiles = (map as any)._osmTiles

    if (activeTileLayer === 'DARK') {
      if (map.hasLayer(osmTiles)) map.removeLayer(osmTiles)
      if (!map.hasLayer(darkTiles)) darkTiles.addTo(map)
    } else {
      if (map.hasLayer(darkTiles)) map.removeLayer(darkTiles)
      if (!map.hasLayer(osmTiles)) osmTiles.addTo(map)
    }
  }, [activeTileLayer])

  // Update Markers and Routes
  useEffect(() => {
    const map = mapInstanceRef.current
    const markersLayer = markersLayerRef.current
    const routesLayer = routesLayerRef.current
    if (!map || !markersLayer || !routesLayer) return

    markersLayer.clearLayers()
    routesLayer.clearLayers()

    // 1. Start Point Marker (Green)
    if (startPoint && startPoint.lat && startPoint.lon) {
      const startHtml = `
        <div class="relative flex items-center justify-center w-8 h-8 rounded-full bg-emerald-500/20 border-2 border-emerald-400 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.5)] cursor-pointer">
          <div class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping absolute"></div>
          <span class="text-xs font-bold font-mono">S</span>
        </div>
      `
      const startMarker = L.marker([startPoint.lat, startPoint.lon], {
        icon: createDivIcon(startHtml, 'start-marker', [32, 32]),
        draggable: interactive,
      }).addTo(markersLayer)

      startMarker.bindPopup(`
        <div class="font-sans text-xs">
          <strong class="text-emerald-400">START POINT</strong><br/>
          ${startPoint.name || 'Custom Launch Point'}<br/>
          Lat: ${startPoint.lat.toFixed(5)}, Lon: ${startPoint.lon.toFixed(5)}
        </div>
      `)

      if (interactive && onStartChange) {
        startMarker.on('dragend', (e) => {
          const latlng = e.target.getLatLng()
          onStartChange({ lat: Number(latlng.lat.toFixed(6)), lon: Number(latlng.lng.toFixed(6)), alt: startPoint.alt })
        })
      }
    }

    // 2. Destination Marker (Red)
    if (destination && destination.lat && destination.lon) {
      const destHtml = `
        <div class="relative flex items-center justify-center w-8 h-8 rounded-full bg-rose-500/20 border-2 border-rose-500 text-rose-300 shadow-[0_0_15px_rgba(244,63,94,0.5)] cursor-pointer">
          <span class="text-xs font-bold font-mono">D</span>
        </div>
      `
      const destMarker = L.marker([destination.lat, destination.lon], {
        icon: createDivIcon(destHtml, 'dest-marker', [32, 32]),
        draggable: interactive,
      }).addTo(markersLayer)

      destMarker.bindPopup(`
        <div class="font-sans text-xs">
          <strong class="text-rose-400">DESTINATION</strong><br/>
          ${destination.name || 'Target Sector'}<br/>
          Lat: ${destination.lat.toFixed(5)}, Lon: ${destination.lon.toFixed(5)}
        </div>
      `)

      if (interactive && onDestinationChange) {
        destMarker.on('dragend', (e) => {
          const latlng = e.target.getLatLng()
          onDestinationChange({ lat: Number(latlng.lat.toFixed(6)), lon: Number(latlng.lng.toFixed(6)), alt: destination.alt })
        })
      }
    }

    // 3. Intermediate Waypoint Markers (Cyan/Blue Numbered)
    waypoints.forEach((wp, idx) => {
      const wpHtml = `
        <div class="flex items-center justify-center w-7 h-7 rounded-full bg-sky-500/20 border-2 border-sky-400 text-sky-300 shadow-[0_0_12px_rgba(14,165,233,0.4)] cursor-pointer">
          <span class="text-xs font-mono font-bold">${idx + 1}</span>
        </div>
      `
      const wpMarker = L.marker([wp.lat, wp.lon], {
        icon: createDivIcon(wpHtml, 'wp-marker', [28, 28]),
        draggable: interactive,
      }).addTo(markersLayer)

      wpMarker.bindPopup(`
        <div class="font-sans text-xs">
          <strong class="text-sky-400">MONITORING WAYPOINT ${idx + 1}</strong><br/>
          ${wp.name || `Waypoint ${idx + 1}`}<br/>
          Lat: ${wp.lat.toFixed(5)}, Lon: ${wp.lon.toFixed(5)}
        </div>
      `)

      if (interactive && onWaypointUpdate) {
        wpMarker.on('dragend', (e) => {
          const latlng = e.target.getLatLng()
          onWaypointUpdate(idx, { lat: Number(latlng.lat.toFixed(6)), lon: Number(latlng.lng.toFixed(6)), alt: wp.alt, name: wp.name })
        })
      }
    })

    // 4. Obstacles Layer (Red Warning Circles on Map)
    if (routePlan?.static_obstacles) {
      routePlan.static_obstacles.forEach((obs: any) => {
        if (obs.lat && obs.lon) {
          const radiusM = obs.radius_m || 250 // Real world visual representation radius
          L.circle([obs.lat, obs.lon], {
            radius: radiusM,
            color: '#ef4444',
            weight: 2,
            fillColor: '#ef4444',
            fillOpacity: 0.25,
            dashArray: '5, 5',
          }).addTo(markersLayer).bindPopup(`
            <div class="font-sans text-xs">
              <strong class="text-rose-400">SIMULATED OBSTACLE REGION</strong><br/>
              ID: ${obs.id}<br/>
              Zone: Dense Canopy / Elephant Migration Corridor<br/>
              Clearance Radius: ${radiusM} m
            </div>
          `)
        }
      })
    }

    // 5. Route Polylines
    // A. Initial / Unoptimized Route (Blue Dashed)
    if (startPoint.lat && destination.lat) {
      const directPoints: [number, number][] = [
        [startPoint.lat, startPoint.lon],
        ...waypoints.map((w) => [w.lat, w.lon] as [number, number]),
        [destination.lat, destination.lon],
      ]
      L.polyline(directPoints, {
        color: '#0284c7',
        weight: 2,
        opacity: 0.6,
        dashArray: '6, 6',
      }).addTo(routesLayer)
    }

    // B. Optimized Route from Global Planner (Green Line)
    if (routePlan?.intermediate_path_points && routePlan.intermediate_path_points.length > 0) {
      const plannedGpsPoints: [number, number][] = routePlan.intermediate_path_points
        .filter((pt: any) => pt.lat !== undefined && pt.lon !== undefined)
        .map((pt: any) => [pt.lat, pt.lon] as [number, number])

      if (plannedGpsPoints.length > 1) {
        L.polyline(plannedGpsPoints, {
          color: '#10b981',
          weight: 4,
          opacity: 0.85,
        }).addTo(routesLayer)
      }
    }

    // C. Actual UAV Trajectory (White Line)
    if (actualTrajectory && actualTrajectory.length > 1) {
      const trajPoints = actualTrajectory.map((p) => [p.lat, p.lon] as [number, number])
      L.polyline(trajPoints, {
        color: '#ffffff',
        weight: 3,
        opacity: 0.95,
      }).addTo(routesLayer)
    }
  }, [startPoint, destination, waypoints, routePlan, actualTrajectory, interactive, activeMode])

  // Update Moving UAV Marker from Telemetry
  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map) return

    const pos = telemetry?.position as any
    if (pos && pos.lat && pos.lon) {
      const heading = telemetry?.closest_obstacle_bearing_deg || 0
      const isAvoiding = telemetry?.flight_state === 'AVOIDING_OBSTACLE'

      const uavHtml = `
        <div class="relative flex items-center justify-center w-10 h-10 -ml-1 -mt-1 cursor-pointer">
          <div class="absolute w-8 h-8 rounded-full ${
            isAvoiding ? 'bg-amber-500/40 border-amber-400' : 'bg-sky-500/30 border-sky-400'
          } border-2 shadow-[0_0_20px_rgba(14,165,233,0.8)] animate-pulse"></div>
          <svg class="w-6 h-6 text-white drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)] transition-transform duration-300"
               style="transform: rotate(${heading}deg);" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2L4.5 20.29l.71.71L12 18l6.79 3 .71-.71z" />
          </svg>
        </div>
      `

      if (uavMarkerRef.current) {
        uavMarkerRef.current.setLatLng([pos.lat, pos.lon])
        uavMarkerRef.current.setIcon(createDivIcon(uavHtml, 'uav-marker', [40, 40]))
      } else {
        const marker = L.marker([pos.lat, pos.lon], {
          icon: createDivIcon(uavHtml, 'uav-marker', [40, 40]),
          zIndexOffset: 1000,
        }).addTo(map)
        marker.bindPopup(`
          <div class="font-sans text-xs">
            <strong class="text-sky-400">ACTIVE UAV</strong><br/>
            State: ${telemetry?.flight_state}<br/>
            Speed: ${telemetry?.velocity.speed.toFixed(1)} m/s<br/>
            Altitude: ${pos.alt?.toFixed(1) || 10.0} m
          </div>
        `)
        uavMarkerRef.current = marker
      }
    }
  }, [telemetry])

  // Search Indian Reserves & Cities
  const handleSearch = (query: string) => {
    setSearchQuery(query)
    if (!query.trim()) {
      setSearchResults([])
      setIsSearching(false)
      return
    }
    setIsSearching(true)
    const matches = INDIAN_WILDLIFE_RESERVES.filter(
      (r) =>
        r.name?.toLowerCase().includes(query.toLowerCase()) ||
        r.description?.toLowerCase().includes(query.toLowerCase())
    )
    setSearchResults(matches)
  }

  const handleSelectSearchResult = (res: GeoCoordinate) => {
    const map = mapInstanceRef.current
    if (map) {
      map.flyTo([res.lat, res.lon], 12, { duration: 1.5 })
    }
    if (activeMode === 'SELECT_START' && onStartChange) {
      onStartChange(res)
    } else if (activeMode === 'SELECT_DEST' && onDestinationChange) {
      onDestinationChange(res)
    } else if (onWaypointAdd) {
      onWaypointAdd(res)
    }
    setSearchQuery('')
    setIsSearching(false)
  }

  const handleRecenterIndia = () => {
    const map = mapInstanceRef.current
    if (map) {
      map.flyTo(INDIA_CENTER_COORDINATES, 5, { duration: 1.2 })
    }
  }

  const handleFitRouteBounds = () => {
    const map = mapInstanceRef.current
    if (!map) return
    const allPts: [number, number][] = []
    if (startPoint.lat) allPts.push([startPoint.lat, startPoint.lon])
    if (destination.lat) allPts.push([destination.lat, destination.lon])
    waypoints.forEach((w) => allPts.push([w.lat, w.lon]))
    if (allPts.length > 0) {
      map.fitBounds(L.latLngBounds(allPts), { padding: [50, 50], maxZoom: 14 })
    }
  }

  return (
    <div className="relative w-full rounded-xl overflow-hidden border border-slate-800 bg-[#090d16] shadow-2xl flex flex-col" style={{ height }}>
      {/* Top Map HUD Overlay Header */}
      <div className="absolute top-3 left-3 right-3 z-[1000] flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        {/* Search Bar */}
        <div className="relative w-72 pointer-events-auto">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/95 border border-slate-700/80 shadow-lg backdrop-blur-md">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search India sanctuaries, parks, cities..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="bg-transparent text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none w-full"
            />
          </div>

          {/* Autocomplete Dropdown */}
          {isSearching && searchResults.length > 0 && (
            <div className="absolute left-0 right-0 top-10 mt-1 max-h-60 overflow-y-auto rounded-lg bg-slate-900/98 border border-slate-700 shadow-2xl backdrop-blur-md z-50">
              {searchResults.map((res, i) => (
                <button
                  key={i}
                  onClick={() => handleSelectSearchResult(res)}
                  className="w-full text-left px-3 py-2 text-xs hover:bg-sky-500/20 border-b border-slate-800/60 last:border-b-0 transition-colors"
                >
                  <div className="font-semibold text-slate-200">{res.name}</div>
                  <div className="text-[10px] text-slate-400 font-mono">{res.description}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Action Mode Switcher */}
        {interactive && (
          <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-900/95 border border-slate-700/80 shadow-lg backdrop-blur-md pointer-events-auto">
            <button
              onClick={() => handleModeChange('SELECT_START')}
              className={`px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors flex items-center gap-1.5 ${
                activeMode === 'SELECT_START'
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Crosshair className="w-3.5 h-3.5" />
              Set Start
            </button>
            <button
              onClick={() => handleModeChange('ADD_WAYPOINT')}
              className={`px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors flex items-center gap-1.5 ${
                activeMode === 'ADD_WAYPOINT'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <MapPin className="w-3.5 h-3.5" />
              Add Waypoint
            </button>
            <button
              onClick={() => handleModeChange('SELECT_DEST')}
              className={`px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors flex items-center gap-1.5 ${
                activeMode === 'SELECT_DEST'
                  ? 'bg-rose-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Flag className="w-3.5 h-3.5" />
              Set Destination
            </button>
          </div>
        )}

        {/* View Controls */}
        <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-900/95 border border-slate-700/80 shadow-lg backdrop-blur-md pointer-events-auto">
          <button
            onClick={() => setActiveTileLayer(activeTileLayer === 'DARK' ? 'OSM' : 'DARK')}
            title="Toggle Map Tile Theme (Dark GCS / Street OSM)"
            className="p-1.5 text-slate-300 hover:text-white rounded hover:bg-slate-800 transition-colors"
          >
            <Layers className="w-4 h-4" />
          </button>
          <button
            onClick={handleFitRouteBounds}
            title="Fit Route Waypoints"
            className="p-1.5 text-slate-300 hover:text-white rounded hover:bg-slate-800 transition-colors"
          >
            <Crosshair className="w-4 h-4" />
          </button>
          <button
            onClick={handleRecenterIndia}
            title="Recenter India National View"
            className="p-1.5 text-slate-300 hover:text-white rounded hover:bg-slate-800 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Map DOM Container */}
      <div ref={mapContainerRef} className="w-full flex-1 z-0" />

      {/* Interactive Legend Box (Bottom Left) */}
      <div className="absolute bottom-3 left-3 z-[1000] p-3 rounded-lg bg-slate-950/90 border border-slate-800/90 shadow-xl backdrop-blur-md text-[11px] font-mono space-y-1.5 pointer-events-none">
        <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider mb-1 flex items-center gap-1">
          <Compass className="w-3 h-3 text-sky-400" />
          INDIA UAV TACTICAL MAP LEGEND
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400"></div>
          <span className="text-slate-300">Start Location (Green)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-rose-500"></div>
          <span className="text-slate-300">Destination (Red)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-sky-400"></div>
          <span className="text-slate-300">Surveillance Waypoints</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-emerald-400"></div>
          <span className="text-slate-300">Optimized Safe Route</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-sky-400 border-dashed border-t border-sky-400"></div>
          <span className="text-slate-300">Initial Planned Route</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-white"></div>
          <span className="text-slate-300">Actual UAV Trajectory</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-rose-500/40 border border-rose-500"></div>
          <span className="text-slate-300">Canopy / Wildlife Obstacle</span>
        </div>
      </div>
    </div>
  )
}
