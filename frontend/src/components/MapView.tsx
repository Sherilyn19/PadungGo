import maplibregl, { type GeoJSONSource, type Map as MLMap } from 'maplibre-gl'
import { useEffect, useRef } from 'react'
import type { JourneyOption, LatLng, Place } from '../api'
import { RIDE_COLORS } from '../journeySteps'

// OpenFreeMap: free OpenStreetMap-based tiles, no API key. Attribution is
// rendered by MapLibre from the style.
const STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty'
const CEBU_CENTER: [number, number] = [123.9, 10.31]
// Respect the OS "reduce motion" setting for camera moves.
const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

interface Props {
  origin: Place | null
  destination: Place | null
  option: JourneyOption | null
  onMapClick: ((p: LatLng) => void) | null
}

interface Feature {
  type: 'Feature'
  geometry: { type: 'LineString'; coordinates: [number, number][] }
  properties: { kind: string; color: string }
}

function toFeatures(option: JourneyOption | null): Feature[] {
  if (!option) return []
  const features: Feature[] = []
  let rideIndex = 0
  for (const seg of option.segments) {
    if (seg.mode === 'ride') {
      const color = RIDE_COLORS[rideIndex++ % RIDE_COLORS.length]
      if (seg.geometry) {
        features.push({
          type: 'Feature',
          geometry: seg.geometry,
          properties: { kind: 'ride', color },
        })
      }
    } else if (seg.start && seg.end) {
      // Approximate connector only; drawn dashed and labelled "not a verified walk".
      features.push({
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [seg.start.longitude, seg.start.latitude],
            [seg.end.longitude, seg.end.latitude],
          ],
        },
        properties: { kind: 'walk', color: '#64748b' },
      })
    }
  }
  return features
}

export default function MapView({ origin, destination, option, onMapClick }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<MLMap | null>(null)
  const markers = useRef<maplibregl.Marker[]>([])
  const clickHandler = useRef(onMapClick)
  clickHandler.current = onMapClick

  useEffect(() => {
    if (!container.current) return
    const m = new maplibregl.Map({
      container: container.current,
      style: STYLE_URL,
      center: CEBU_CENTER,
      zoom: 12.5,
    })
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    m.on('load', () => {
      m.addSource('journey', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({
        id: 'journey-walk',
        type: 'line',
        source: 'journey',
        filter: ['==', ['get', 'kind'], 'walk'],
        paint: { 'line-color': ['get', 'color'], 'line-width': 3, 'line-dasharray': [1, 2] },
      })
      m.addLayer({
        id: 'journey-ride',
        type: 'line',
        source: 'journey',
        filter: ['==', ['get', 'kind'], 'ride'],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': ['get', 'color'], 'line-width': 5, 'line-opacity': 0.9 },
      })
    })
    m.on('click', (e) => clickHandler.current?.({ latitude: e.lngLat.lat, longitude: e.lngLat.lng }))
    map.current = m
    return () => m.remove()
  }, [])

  useEffect(() => {
    const m = map.current
    if (!m) return
    m.getCanvas().style.cursor = onMapClick ? 'crosshair' : ''
  }, [onMapClick])

  useEffect(() => {
    const m = map.current
    if (!m) return
    markers.current.forEach((mk) => mk.remove())
    markers.current = []
    const pts: [Place | null, string, string][] = [
      [origin, '#059669', 'Start'],
      [destination, '#dc2626', 'Destination'],
    ]
    for (const [p, color, title] of pts) {
      if (!p) continue
      const mk = new maplibregl.Marker({ color })
        .setLngLat([p.longitude, p.latitude])
        .setPopup(new maplibregl.Popup({ offset: 24 }).setText(`${title}: ${p.name}`))
        .addTo(m)
      markers.current.push(mk)
    }
  }, [origin, destination])

  useEffect(() => {
    const m = map.current
    if (!m) return
    const apply = () => {
      const src = m.getSource('journey') as GeoJSONSource | undefined
      if (!src) return
      const features = toFeatures(option)
      src.setData({ type: 'FeatureCollection', features })
      const coords = features.flatMap((f) => f.geometry.coordinates)
      for (const p of [origin, destination]) if (p) coords.push([p.longitude, p.latitude])
      if (coords.length >= 2) {
        const bounds = coords.reduce(
          (b, c) => b.extend(c as [number, number]),
          new maplibregl.LngLatBounds(coords[0] as [number, number], coords[0] as [number, number]),
        )
        m.fitBounds(bounds, { padding: 60, maxZoom: 16, duration: prefersReducedMotion() ? 0 : 600 })
      }
    }
    if (m.isStyleLoaded() && m.getSource('journey')) apply()
    else m.once('idle', apply)
  }, [option, origin, destination])

  return (
    <div className="relative h-full w-full">
      <div ref={container} className="h-full w-full" aria-label="Map of Metro Cebu" role="region" />
      {option && (
        <div className="pointer-events-none absolute bottom-8 left-2 rounded-md bg-white/90 px-2 py-1 text-xs text-slate-700 shadow">
          <span className="font-semibold text-emerald-700">━</span> ride (route shape) ·{' '}
          <span className="text-slate-500">┄</span> walk (straight line, not a verified path)
        </div>
      )}
    </div>
  )
}
