import { ArrowDownToDot, ArrowRightLeft, BusFront, CircleDot, Flag, Minus, Plus, Scan, type LucideIcon } from 'lucide-react'
import maplibregl, { type GeoJSONSource, type Map as MLMap } from 'maplibre-gl'
import { createElement, useCallback, useEffect, useRef, useState } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import type { JourneyOption, LatLng, Place } from '../../api'
import { rideColor } from '../../tripTimeline'
import MapCredits from './MapCredits'
import { tripMarkers, type TripMarkerKind } from './tripMarkers'

// OpenFreeMap: free OpenStreetMap-based tiles, no API key. Its required
// OpenFreeMap / OpenMapTiles / OpenStreetMap credit is listed in MapCredits.
const STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty'
const CEBU_CENTER: [number, number] = [123.9, 10.31]
const WALK_COLOR = '#6f7c89'
const CREDITS_VISIBLE_MS = 5000

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

export interface MapInsets {
  left: number
  bottom: number
}

interface Props {
  origin: Place | null
  destination: Place | null
  option: JourneyOption | null
  onMapClick: ((p: LatLng) => void) | null
  insets: MapInsets
}

interface LineFeature {
  type: 'Feature'
  geometry: { type: 'LineString'; coordinates: [number, number][] }
  properties: { kind: 'ride' | 'walk'; color: string }
}

function toFeatures(option: JourneyOption | null): LineFeature[] {
  if (!option) return []
  const features: LineFeature[] = []
  let rideIndex = 0
  for (const seg of option.segments) {
    if (seg.mode === 'ride') {
      const color = rideColor(rideIndex++)
      if (seg.geometry) features.push({ type: 'Feature', geometry: seg.geometry, properties: { kind: 'ride', color } })
    } else if (seg.start && seg.end) {
      // Approximate straight-line connector only; drawn dotted.
      features.push({
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [seg.start.longitude, seg.start.latitude],
            [seg.end.longitude, seg.end.latitude],
          ],
        },
        properties: { kind: 'walk', color: WALK_COLOR },
      })
    }
  }
  return features
}

type MarkerKind = TripMarkerKind | 'origin' | 'destination'

const MARKER_ICON: Record<MarkerKind, LucideIcon> = {
  origin: CircleDot,
  destination: Flag,
  board: BusFront,
  transfer: ArrowRightLeft,
  alight: ArrowDownToDot,
}

// Builds a marker element with a Lucide icon, styled to match the timeline.
function markerElement(kind: MarkerKind, color: string, label: string): { el: HTMLElement; root: Root } {
  const el = document.createElement('div')
  el.setAttribute('role', 'img')
  el.setAttribute('aria-label', label)
  el.title = label
  const inner = document.createElement('div')
  const shape: Record<MarkerKind, string> = {
    origin: 'h-8 w-8 rounded-full border-[3px] border-brand-500 bg-white text-brand-600',
    destination: 'h-9 w-9 rounded-full border-2 border-white bg-alert text-white',
    board: 'h-7 w-7 rounded-full border-2 border-white text-white',
    transfer: 'h-7 w-7 rounded-[5px] border-2 border-white bg-brand-950 text-white',
    alight: 'h-6 w-6 rounded-full border-[2.5px] bg-white',
  }
  inner.className = `map-marker flex cursor-pointer items-center justify-center shadow-[0_2px_6px_rgb(6_47_87/0.35)] transition-transform duration-150 hover:scale-110 ${shape[kind]}`
  if (kind === 'board') inner.style.backgroundColor = color
  if (kind === 'alight') {
    inner.style.borderColor = color
    inner.style.color = color
  }
  el.appendChild(inner)
  const root = createRoot(inner)
  const size = kind === 'alight' ? 13 : kind === 'destination' ? 18 : 15
  root.render(createElement(MARKER_ICON[kind], { size, strokeWidth: 2.5, 'aria-hidden': true }))
  return { el, root }
}

interface PlacedMarker {
  marker: maplibregl.Marker
  root: Root
}

function clearMarkers(list: PlacedMarker[]) {
  for (const { marker, root } of list) {
    marker.remove()
    // Unmount after React finishes the current commit.
    queueMicrotask(() => root.unmount())
  }
  list.length = 0
}

export default function MapView({ origin, destination, option, onMapClick, insets }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<MLMap | null>(null)
  const endpointMarkers = useRef<PlacedMarker[]>([])
  const stopMarkers = useRef<PlacedMarker[]>([])
  const clickHandler = useRef(onMapClick)
  clickHandler.current = onMapClick
  const insetsRef = useRef(insets)
  insetsRef.current = insets
  const fitTarget = useRef<[number, number][]>([])
  const [creditsOpen, setCreditsOpen] = useState(true)

  useEffect(() => {
    if (!container.current) return
    const m = new maplibregl.Map({
      container: container.current,
      style: STYLE_URL,
      center: CEBU_CENTER,
      zoom: 12.5,
      attributionControl: false,
    })
    // Credits show at start, then fold into the (i) button on first interaction.
    // Only the user's own drag/zoom counts; the map also moves itself on load.
    const foldOnUserMove = (e: { originalEvent?: unknown }) => {
      if (!e.originalEvent) return
      setCreditsOpen(false)
      m.off('movestart', foldOnUserMove)
    }
    m.on('movestart', foldOnUserMove)
    m.once('click', () => setCreditsOpen(false))
    m.on('load', () => {
      m.addSource('journey', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({
        id: 'journey-walk',
        type: 'line',
        source: 'journey',
        filter: ['==', ['get', 'kind'], 'walk'],
        layout: { 'line-cap': 'round' },
        paint: { 'line-color': ['get', 'color'], 'line-width': 3, 'line-dasharray': [0.5, 2], 'line-opacity': 0.9 },
      })
      // A static, route-colored halo shares the journey source: no animation loop.
      m.addLayer({
        id: 'journey-ride-aura',
        type: 'line',
        source: 'journey',
        filter: ['==', ['get', 'kind'], 'ride'],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': ['get', 'color'], 'line-width': 22, 'line-blur': 9, 'line-opacity': 0.38 },
      })
      // White casing under the ride line keeps it crisp over busy streets.
      m.addLayer({
        id: 'journey-ride-casing',
        type: 'line',
        source: 'journey',
        filter: ['==', ['get', 'kind'], 'ride'],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#ffffff', 'line-width': 9, 'line-opacity': 0.95 },
      })
      m.addLayer({
        id: 'journey-ride',
        type: 'line',
        source: 'journey',
        filter: ['==', ['get', 'kind'], 'ride'],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': ['get', 'color'], 'line-width': 5 },
      })
    })
    m.on('click', (e) => clickHandler.current?.({ latitude: e.lngLat.lat, longitude: e.lngLat.lng }))
    // The sidebar can be dragged or collapsed, so follow the container size.
    const observer = new ResizeObserver(() => m.resize())
    observer.observe(container.current)
    map.current = m
    return () => {
      observer.disconnect()
      clearMarkers(endpointMarkers.current)
      clearMarkers(stopMarkers.current)
      m.remove()
    }
  }, [])

  useEffect(() => {
    const m = map.current
    if (m) m.getCanvas().style.cursor = onMapClick ? 'crosshair' : ''
  }, [onMapClick])

  const fit = useCallback((animate: boolean) => {
    const m = map.current
    const coords = fitTarget.current
    if (!m || coords.length === 0) return
    const { left, bottom } = insetsRef.current
    const padding = { top: 72, right: 64, bottom: 40 + bottom, left: 48 + left }
    const duration = animate && !prefersReducedMotion() ? 900 : 0
    if (coords.length === 1) {
      m.easeTo({ center: coords[0], zoom: Math.max(m.getZoom(), 14), padding, duration })
      return
    }
    const bounds = coords.reduce(
      (b, c) => b.extend(c),
      new maplibregl.LngLatBounds(coords[0], coords[0]),
    )
    m.fitBounds(bounds, { padding, maxZoom: 16, duration })
  }, [])

  // Start and destination markers.
  useEffect(() => {
    const m = map.current
    if (!m) return
    clearMarkers(endpointMarkers.current)
    const points: [Place | null, MarkerKind, string][] = [
      [origin, 'origin', 'Start'],
      [destination, 'destination', 'Destination'],
    ]
    for (const [p, kind, title] of points) {
      if (!p) continue
      const label = `${title}: ${p.name}`
      const { el, root } = markerElement(kind, '', label)
      const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
        .setLngLat([p.longitude, p.latitude])
        .setPopup(new maplibregl.Popup({ offset: 20, closeButton: false }).setText(label))
        .addTo(m)
      endpointMarkers.current.push({ marker, root })
    }
  }, [origin, destination])

  // Trip lines and stop markers; refit only when the shown trip or endpoints change.
  useEffect(() => {
    const m = map.current
    if (!m) return
    const apply = () => {
      const src = m.getSource('journey') as GeoJSONSource | undefined
      if (!src) return
      const features = toFeatures(option)
      const fade = !prefersReducedMotion()
      // Fade the new trip in so switching alternatives reads as one change.
      m.setPaintProperty('journey-ride', 'line-opacity-transition', { duration: 0, delay: 0 })
      m.setPaintProperty('journey-ride', 'line-opacity', fade ? 0 : 0.95)
      src.setData({ type: 'FeatureCollection', features })
      if (fade) {
        requestAnimationFrame(() => {
          m.setPaintProperty('journey-ride', 'line-opacity-transition', { duration: 450, delay: 150 })
          m.setPaintProperty('journey-ride', 'line-opacity', 0.95)
        })
      }

      clearMarkers(stopMarkers.current)
      for (const stop of tripMarkers(option)) {
        const { el, root } = markerElement(stop.kind, stop.color, stop.label)
        const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
          .setLngLat([stop.point.longitude, stop.point.latitude])
          .setPopup(new maplibregl.Popup({ offset: 16, closeButton: false }).setText(stop.label))
          .addTo(m)
        stopMarkers.current.push({ marker, root })
      }

      const coords = features.flatMap((f) => f.geometry.coordinates)
      for (const p of [origin, destination]) if (p) coords.push([p.longitude, p.latitude])
      fitTarget.current = coords
      fit(true)
    }
    if (m.isStyleLoaded() && m.getSource('journey')) apply()
    else m.once('idle', apply)
  }, [option, origin, destination, fit])

  // Also fold the credits after five seconds, as the OSM guideline allows.
  useEffect(() => {
    const timer = window.setTimeout(() => setCreditsOpen(false), CREDITS_VISIBLE_MS)
    return () => window.clearTimeout(timer)
  }, [])

  const overlayLimit = Math.round(window.innerHeight * 0.55)
  const control =
    'focus-ring flex h-9 w-9 items-center justify-center bg-white text-brand-600 transition-colors hover:bg-brand-50 active:bg-brand-100'

  return (
    // A fully open phone sheet would push the corner overlays to the top of the
    // screen; past ~half height they stay behind the sheet instead.
    <div className="relative h-full w-full" style={{ ['--map-bottom-inset' as string]: `${Math.min(insets.bottom, overlayLimit)}px` }}>
      <div ref={container} className="h-full w-full" aria-label="Map of Metro Cebu" role="region" />
      {option && insets.bottom <= overlayLimit && (
        <div
          className="fade-up pointer-events-none absolute left-3 z-10 flex items-center gap-3 rounded-[4px] border border-line bg-white/95 px-2.5 py-1.5 text-[11px] text-ink-muted shadow-[0_2px_6px_rgb(6_47_87/0.12)] transition-[bottom] duration-300"
          // Above the bottom sheet on phones.
          style={{ bottom: insets.bottom ? insets.bottom + 40 : 12 }}
        >
          <span className="flex items-center gap-1.5">
            <span className="h-1 w-5 rounded-full bg-brand-500" aria-hidden="true" />
            Jeepney ride
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-5 border-t-2 border-dotted border-ink-soft" aria-hidden="true" />
            Walk
          </span>
        </div>
      )}
      <div className="absolute top-3 right-3 z-10 flex flex-col overflow-hidden rounded-[4px] border border-line-strong shadow-[0_2px_6px_rgb(6_47_87/0.15)]">
        <button type="button" className={control} aria-label="Zoom in" title="Zoom in" onClick={() => map.current?.zoomIn()}>
          <Plus size={18} aria-hidden="true" />
        </button>
        <button type="button" className={`${control} border-t border-line`} aria-label="Zoom out" title="Zoom out" onClick={() => map.current?.zoomOut()}>
          <Minus size={18} aria-hidden="true" />
        </button>
        <button
          type="button"
          className={`${control} border-t border-line`}
          aria-label="Fit the trip on screen"
          title="Fit the trip on screen"
          onClick={() => fit(true)}
        >
          <Scan size={17} aria-hidden="true" />
        </button>
      </div>
      <MapCredits open={creditsOpen} onOpenChange={setCreditsOpen} />
    </div>
  )
}
