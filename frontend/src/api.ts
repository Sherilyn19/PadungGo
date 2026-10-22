// Typed client for the PadungGo API (docs/API_DESIGN.md). No secrets here:
// VITE_API_BASE_URL is public by design.

export const API_BASE: string = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'
).replace(/\/+$/, '')

export interface LatLng {
  latitude: number
  longitude: number
}

export interface Place extends LatLng {
  id?: string
  name: string
  source: 'search' | 'gps' | 'map'
}

export interface LocationResult extends LatLng {
  id: string
  name: string
  kind: string
  area: string | null
  status: string
}

export interface LineGeometry {
  type: 'LineString'
  coordinates: [number, number][]
}

interface BaseSegment {
  instruction: string
  distance_m: number | null
  duration_seconds: number | null
  estimate_basis: string | null
  start?: LatLng
  end?: LatLng
}

export interface WalkSegment extends BaseSegment {
  mode: 'walk'
  straight_line_m: number
}

export interface TransferSegment extends BaseSegment {
  mode: 'transfer_walk'
  from_stop_id?: string
  to_stop_id?: string
}

export type FareStatus = 'exact' | 'approximate' | 'unavailable'

export interface FareAmount {
  amount_centavos: number | null
  status: FareStatus
  reason: string | null
  // Passenger category the verified quote was made for (backend default: regular).
  passenger_category?: string
  // Set only when an admin-verified fare rule produced the amount.
  rule_id?: string | null
}

// Estimates from the LTFRB PUJ fare guides (effective 2026-09-28), computed
// by the backend for every ride. Contract: docs/API_DESIGN.md, "Guide fare
// estimates". The frontend only picks and adds these amounts; it never
// calculates a fare itself.
export type GuideVehicleType = 'traditional' | 'modern'
export type GuideFareColumn = 'regular' | 'discounted'

export interface GuideFareEstimate {
  status: 'available' | 'unavailable'
  // Machine-readable cause when unavailable, e.g. "beyond_guide_range".
  reason: string | null
  guide_effective_date: string
  chargeable_km: number | null
  // Only set when admin-verified evidence confirms the vehicle type.
  known_vehicle_type: GuideVehicleType | null
  amounts_centavos: Record<GuideVehicleType, Record<GuideFareColumn, number>> | null
}

export interface RideSegment extends BaseSegment {
  mode: 'ride'
  route_id: string
  route_code: string
  route_name: string
  signboard: string | null
  vehicle_class: string
  operator: string | null
  direction: string
  verification_status: string
  board_stop_name: string
  alight_stop_name: string
  geometry: LineGeometry | null
  fare: FareAmount
  // Missing on backends deployed before guide estimates existed.
  guide_fare_estimate?: GuideFareEstimate | null
}

export type Segment = WalkSegment | TransferSegment | RideSegment

export interface JourneyOption {
  id: string
  transfers: number
  labels: string[]
  segments: Segment[]
  fare: {
    currency: string
    total_centavos: number | null
    known_subtotal_centavos: number
    total_is_complete: boolean
    status: FareStatus
    reason: string | null
  }
  time: {
    walking_seconds: number | null
    waiting_seconds: number | null
    riding_seconds: number | null
    total_seconds: number | null
    known_subtotal_seconds: number
    total_is_complete: boolean
    uncertainty_notes: string[]
  }
  evidence: {
    verification_status: string
    references: { title?: string; publisher?: string; reference?: string }[]
  }
  warnings: string[]
}

export interface PlanResponse {
  request_coverage_status: string
  reason: string | null
  journey_options: JourneyOption[]
  ranking: { requested: string; applied: string; warning: string | null }
  warnings: string[]
}

// Mirrors MAX_JOURNEY_OPTIONS in backend/transit/planner/validation.py.
export const MAX_JOURNEY_OPTIONS = 50

export type SortBy = 'fewest_transfers' | 'cheapest' | 'fastest' | 'least_walking'

export class ApiError extends Error {
  readonly status: number
  readonly retryable: boolean
  readonly fields: Record<string, string[]> | null
  constructor(message: string, status: number, retryable: boolean, fields: Record<string, string[]> | null = null) {
    super(message)
    this.status = status
    this.retryable = retryable
    this.fields = fields
  }
}

// The free backend sleeps when idle and can take ~1 minute to wake up.
const TIMEOUT_MS = 90_000

async function request<T>(path: string, init?: RequestInit, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  if (signal?.aborted) {
    clearTimeout(timer)
    throw new ApiError('Request cancelled.', 0, false)
  }
  const forwardAbort = () => controller.abort()
  signal?.addEventListener('abort', forwardAbort, { once: true })
  let resp: Response

  try {
    resp = await fetch(API_BASE + path, { ...init, signal: controller.signal })
  } catch {
    if (signal?.aborted) throw new ApiError('Request cancelled.', 0, false)
    throw new ApiError(
      'Can’t connect right now. Check your internet, then try again.',
      0,
      true,
    )
    } finally {
      clearTimeout(timer)
      signal?.removeEventListener('abort', forwardAbort)
    }

  let body: unknown = null
  if (resp.headers.get('content-type')?.includes('application/json')) {
    try {
      body = await resp.json()
    } catch {
      /* Invalid JSON is handled below without exposing the response body. */
    }
  }
  if (!resp.ok) {
    const err = (body as { error?: { message?: string; retryable?: boolean; fields?: Record<string, string[]> } } | null)?.error
    throw new ApiError(
      err?.message ?? ([502, 503, 504].includes(resp.status)
        ? 'PadungGo is busy right now. Please try again in a minute.'
        : 'Something went wrong. Please try again.'),
      resp.status,
      err?.message != null ? (err.retryable ?? resp.status >= 500) : resp.status >= 500,
      err?.fields ?? null,
    )
  }
  if (body === null) {
    throw new ApiError('Something went wrong. Please try again.', resp.status, true)
  }
  return body as T
}

export function searchLocations(q: string, signal?: AbortSignal): Promise<{ results: LocationResult[] }> {
  return request(`/locations?q=${encodeURIComponent(q)}&limit=8`, undefined, signal)
}

// Older API deployments accept at most 5 options.
const LEGACY_JOURNEY_LIMIT = 5

export async function planJourney(
  origin: Place,
  destination: Place,
  sortBy: SortBy,
  maxTransfers: 0 | 1,
): Promise<PlanResponse> {
  const endpoint = (p: Place) =>
    p.id ? { location_id: p.id } : { latitude: p.latitude, longitude: p.longitude }
  const send = (limit: number) =>
    request<PlanResponse>('/journeys/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origin: endpoint(origin),
        destination: endpoint(destination),
        sort_by: sortBy,
        max_transfers: maxTransfers,
        limit,
      }),
    })
  try {
    // Ask for every alternative the planner finds (backend maximum), not a top 5.
    return await send(MAX_JOURNEY_OPTIONS)
  } catch (e) {
    // Keeps the app working if the frontend is deployed before the backend.
    if (e instanceof ApiError && e.status === 400 && e.fields?.limit) return send(LEGACY_JOURNEY_LIMIT)
    throw e
  }
}
