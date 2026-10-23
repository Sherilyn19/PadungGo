// Typed client for the PadungGo API (docs/API_DESIGN.md). No secrets here:
// VITE_API_BASE_URL is public by design.

export const API_BASE: string = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'
).replace(/\/+$/, '')

export interface LatLng {
  latitude: number
  longitude: number
}

// Where a chosen point came from. Planning always uses latitude/longitude
// (or id for PadungGo locations); the name is only a label.
export type PlaceSource = 'search' | 'provider' | 'gps' | 'map'

// For GPS and map points: whether a readable address has been found yet.
export type AddressStatus = 'pending' | 'resolved' | 'unavailable'

export interface Attribution {
  text: string
  url: string | null
}

export interface Place extends LatLng {
  // Only PadungGo location records have an id.
  id?: string
  name: string
  source: PlaceSource
  addressStatus?: AddressStatus
}

export interface PlaceSuggestion extends LatLng {
  // "padunggo": our own location record; "geoapify": a map-data result that
  // says nothing about which routes serve it.
  source: 'padunggo' | 'geoapify'
  location_id: string | null
  name: string
  detail: string | null
  kind: string
  status?: string
  data_attribution?: Attribution
}

export interface SuggestionsResponse {
  results: PlaceSuggestion[]
  provider: {
    name: string
    // ok | skipped | disabled | quota | rate_limited | timeout | error
    status: string
    attribution: Attribution[]
  }
}

export interface AddressResponse extends LatLng {
  status: 'resolved' | 'no_result' | 'unavailable'
  label: string | null
  distance_m: number | null
  // Why no address: disabled | quota | rate_limited | timeout | error
  reason: string | null
  attribution: Attribution[] | null
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
  // "scarce": commuters report few trips. "not_flagged" (or missing, on older
  // backends) only means no report is recorded, not that service is frequent.
  service_availability?: 'scarce' | 'not_flagged'
  // Opaque IDs of this ride. "Explain this trip" sends them back so the
  // server can find the same trip itself. Missing on older backends.
  route_pattern_id?: string
  board_occurrence_id?: string
  alight_occurrence_id?: string
}

export type Segment = WalkSegment | TransferSegment | RideSegment

export interface JourneyOption {
  id: string
  transfers: number
  // True when any ride is scarce. Missing on older backends (treat as false).
  has_scarce_ride?: boolean
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
  // Manila calendar date ("YYYY-MM-DD") of the last route-data change.
  // Missing on older backends; null when the server has no record.
  data_updated_on?: string | null
  // scarce_last: the backend lists trips with a scarce ride after the others,
  // before applying the limit. Missing on older backends (treat as false).
  ranking: { requested: string; applied: string; warning: string | null; scarce_last?: boolean }

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

interface LegacyLocation extends LatLng {
  id: string
  name: string
  kind: string
  area: string | null
  status: string
}

export async function suggestPlaces(q: string, signal?: AbortSignal): Promise<SuggestionsResponse> {
  try {
    return await request<SuggestionsResponse>(`/places/suggestions?q=${encodeURIComponent(q)}`, undefined, signal)
  } catch (e) {
    // Keeps search working if the frontend is deployed before the backend.
    if (!(e instanceof ApiError && e.status === 404)) throw e
    const legacy = await request<{ results: LegacyLocation[] }>(
      `/locations?q=${encodeURIComponent(q)}&limit=8`, undefined, signal)
    return {
      results: legacy.results.map((r) => ({
        source: 'padunggo', location_id: r.id, name: r.name, detail: r.area,
        kind: r.kind, latitude: r.latitude, longitude: r.longitude, status: r.status,
      })),
      provider: { name: 'geoapify', status: 'disabled', attribution: [] },
    }
  }
}

// POST keeps the coordinates out of URLs and server access logs.
export function lookUpAddress(point: LatLng, signal?: AbortSignal): Promise<AddressResponse> {
  return request('/places/address', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ latitude: point.latitude, longitude: point.longitude }),
  }, signal)
}

// Planning always uses an id for saved places, otherwise the coordinates.
function toEndpoint(p: Place) {
  return p.id ? { location_id: p.id } : { latitude: p.latitude, longitude: p.longitude }
}

// Older API deployments accept at most 5 options.
const LEGACY_JOURNEY_LIMIT = 5

export async function planJourney(
  origin: Place,
  destination: Place,
  sortBy: SortBy,
  maxTransfers: 0 | 1,
): Promise<PlanResponse> {
  const send = (limit: number) =>
    request<PlanResponse>('/journeys/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origin: toEndpoint(origin),
        destination: toEndpoint(destination),
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

// --- AI trip explanation (docs/API_DESIGN.md, "Explain this trip") ---------

// The search that produced the trips, so the server can plan again.
export interface TripSearch {
  from: Place
  to: Place
  sortBy: SortBy
  maxTransfers: 0 | 1
}

export interface RideReference {
  route_pattern_id: string
  board_occurrence_id: string
  alight_occurrence_id: string
}

export type ExplainResponse =
  | { status: 'ok'; explanation: string; notices: string[]; ai_generated: true; model: string }
  | { status: 'unavailable'; reason: string; message: string; retryable: boolean }

// The chosen rides as opaque IDs, or null when this backend does not send
// them. Only IDs go to the server; the explanation is built from its own copy
// of the trip, so nothing here can change what the AI is told.
export function rideReferences(option: JourneyOption): RideReference[] | null {
  const refs: RideReference[] = []
  for (const segment of option.segments) {
    if (segment.mode !== 'ride') continue
    const { route_pattern_id, board_occurrence_id, alight_occurrence_id } = segment
    if (!route_pattern_id || !board_occurrence_id || !alight_occurrence_id) return null
    refs.push({ route_pattern_id, board_occurrence_id, alight_occurrence_id })
  }
  return refs.length > 0 ? refs : null
}

export function explainRequestBody(search: TripSearch, rides: RideReference[]) {
  return {
    origin: toEndpoint(search.from),
    destination: toEndpoint(search.to),
    sort_by: search.sortBy,
    max_transfers: search.maxTransfers,
    rides,
  }
}

export async function explainJourney(
  search: TripSearch,
  option: JourneyOption,
  signal?: AbortSignal,
): Promise<unknown> {
  const rides = rideReferences(option)
  if (!rides) throw new ApiError('This trip cannot be explained yet. Please search again.', 0, false)
  return request<unknown>('/journeys/explain', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(explainRequestBody(search, rides)),
  }, signal)
}
