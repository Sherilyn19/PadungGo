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

export type SortBy = 'fewest_transfers' | 'cheapest' | 'fastest' | 'least_walking'

export class ApiError extends Error {
  readonly status: number
  readonly retryable: boolean
  constructor(message: string, status: number, retryable: boolean) {
    super(message)
    this.status = status
    this.retryable = retryable
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
      'Could not reach the PadungGo server. It may be waking up — please try again.',
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
    const err = (body as { error?: { message?: string; retryable?: boolean } } | null)?.error
    throw new ApiError(
      err?.message ?? ([502, 503, 504].includes(resp.status)
        ? 'The PadungGo server is unavailable or starting up. Please try again in a minute.'
        : `The server returned an error (${resp.status}).`),
      resp.status,
      err?.message != null ? (err.retryable ?? resp.status >= 500) : resp.status >= 500,
    )
  }
  if (body === null) {
    throw new ApiError('The server sent an unexpected response. Please try again.', resp.status, true)
  }
  return body as T
}

export function searchLocations(q: string, signal?: AbortSignal): Promise<{ results: LocationResult[] }> {
  return request(`/locations?q=${encodeURIComponent(q)}&limit=8`, undefined, signal)
}

export function planJourney(
  origin: Place,
  destination: Place,
  sortBy: SortBy,
  maxTransfers: 0 | 1,
): Promise<PlanResponse> {
  const endpoint = (p: Place) =>
    p.id ? { location_id: p.id } : { latitude: p.latitude, longitude: p.longitude }
  return request('/journeys/plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      origin: endpoint(origin),
      destination: endpoint(destination),
      sort_by: sortBy,
      max_transfers: maxTransfers,
      limit: 5,
    }),
  })
}
