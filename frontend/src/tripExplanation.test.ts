// @vitest-environment node

import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  ApiError,
  explainJourney,
  explainRequestBody,
  rideReferences,
  type JourneyOption,
  type Place,
  type RideSegment,
  type TripSearch,
} from './api'
import {
  explanationFromError,
  explanationFromResponse,
  parseExplainResponse,
} from './tripExplanation'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

// --- Trips as the planner API returns them (synthetic, test-only) ----------

function ride(code: string, n: number, extra: Partial<RideSegment> = {}): RideSegment {
  return {
    mode: 'ride', instruction: '', distance_m: 4000, duration_seconds: 600, estimate_basis: null,
    route_id: `r${n}`, route_code: code, route_name: 'Plaza - Carbon', signboard: null, vehicle_class: 'jeepney',
    operator: null, direction: 'outbound', verification_status: 'documented',
    board_stop_name: `Board ${code}`, alight_stop_name: `Alight ${code}`, geometry: null,
    fare: { amount_centavos: null, status: 'unavailable', reason: 'No supported fare calculation.' },
    route_pattern_id: `00000000-0000-4000-8000-00000000000${n}`,
    board_occurrence_id: `00000000-0000-4000-8000-0000000001${n}0`,
    alight_occurrence_id: `00000000-0000-4000-8000-0000000002${n}0`,
    ...extra,
  }
}

const walk = { mode: 'walk', instruction: 'Walk', distance_m: null, duration_seconds: null, estimate_basis: null, straight_line_m: 120 }
const transferWalk = { mode: 'transfer_walk', instruction: 'Transfer', distance_m: 60, duration_seconds: null, estimate_basis: null }

const trip = (segments: unknown[], extra: Partial<JourneyOption> = {}) =>
  ({ id: 'opt-1', transfers: segments.filter((s) => (s as { mode: string }).mode === 'transfer_walk').length, segments, ...extra }) as unknown as JourneyOption

const direct = trip([walk, ride('17D', 1), walk])
const oneTransfer = trip([walk, ride('17D', 1), transferWalk, ride('42D', 2), walk])
const scarce = trip([walk, ride('14B', 1, { service_availability: 'scarce' }), walk], { has_scarce_ride: true })
const unknownFareAndWait = trip([walk, ride('17D', 1), walk], {
  fare: { currency: 'PHP', total_centavos: null, known_subtotal_centavos: 0, total_is_complete: false, status: 'unavailable', reason: 'x' },
  time: { walking_seconds: null, waiting_seconds: null, riding_seconds: null, total_seconds: null, known_subtotal_seconds: 0, total_is_complete: false, uncertainty_notes: [] },
})
const historic = trip([walk, ride('17D', 1, { verification_status: 'documented' }), walk], {
  evidence: { verification_status: 'documented', references: [] },
})

const savedPlace: Place = { id: 'loc-1', name: 'Fuente', latitude: 10.31, longitude: 123.89, source: 'search' }
const gpsPlace: Place = { name: 'My location', latitude: 10.2999, longitude: 123.9001, source: 'gps' }
const search: TripSearch = { from: savedPlace, to: gpsPlace, sortBy: 'fewest_transfers', maxTransfers: 1 }

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

// --- What the browser sends --------------------------------------------------

describe('which rides are sent', () => {
  it('sends the one ride of a direct trip', () => {
    expect(rideReferences(direct)).toEqual([
      { route_pattern_id: expect.any(String), board_occurrence_id: expect.any(String), alight_occurrence_id: expect.any(String) },
    ])
  })

  it('sends both rides of a one-transfer trip, in travel order', () => {
    const refs = rideReferences(oneTransfer)!
    expect(refs).toHaveLength(2)
    expect(refs[0].route_pattern_id).toBe(((oneTransfer.segments[1]) as RideSegment).route_pattern_id)
    expect(refs[1].route_pattern_id).toBe(((oneTransfer.segments[3]) as RideSegment).route_pattern_id)
  })

  it('treats trips without ride IDs (older backend) as not explainable', () => {
    const old = trip([walk, ride('17D', 1, { route_pattern_id: undefined }), walk])
    expect(rideReferences(old)).toBeNull()
    expect(rideReferences(trip([walk, walk]))).toBeNull()
  })
})

describe('what the explain request contains', () => {
  it.each([
    ['a direct trip', direct], ['a one-transfer trip', oneTransfer], ['a scarce trip', scarce],
    ['a trip with unknown fare and wait', unknownFareAndWait], ['a historic trip', historic],
  ])('holds only the search and opaque IDs for %s', (_name, option) => {
    const body = explainRequestBody(search, rideReferences(option)!)
    expect(Object.keys(body).sort()).toEqual(['destination', 'max_transfers', 'origin', 'rides', 'sort_by'])
    for (const ride of body.rides) expect(Object.keys(ride).sort()).toEqual(['alight_occurrence_id', 'board_occurrence_id', 'route_pattern_id'])
    // No route facts a client could invent or alter.
    const text = JSON.stringify(body)
    for (const fact of ['route_code', '17D', '42D', '14B', 'Board', 'Alight', 'fare', 'scarce', 'verified', 'Plaza']) {
      expect(text).not.toContain(fact)
    }
  })

  it('sends a saved place by id and a raw point by coordinates only when it has no id', () => {
    const body = explainRequestBody(search, rideReferences(direct)!)
    expect(body.origin).toEqual({ location_id: 'loc-1' })
    expect(body.destination).toEqual({ latitude: 10.2999, longitude: 123.9001 })
    expect(JSON.stringify(body)).not.toContain('Fuente')
  })

  it('repeats the sort and transfer settings used for the plan', () => {
    const body = explainRequestBody({ ...search, sortBy: 'fastest', maxTransfers: 0 }, rideReferences(direct)!)
    expect(body).toMatchObject({ sort_by: 'fastest', max_transfers: 0 })
  })

  it('posts to the explain endpoint using POST so coordinates stay out of URLs', async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({ status: 'unavailable' }))
    vi.stubGlobal('fetch', fetchMock)
    await explainJourney(search, direct)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toMatch(/\/journeys\/explain$/)
    expect(init.method).toBe('POST')
    expect(url).not.toMatch(/10\.2999|123\.9001/)
  })

  it('does not call the server for a trip it cannot identify', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const old = trip([walk, ride('17D', 1, { board_occurrence_id: undefined }), walk])
    await expect(explainJourney(search, old)).rejects.toBeInstanceOf(ApiError)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('can be cancelled', async () => {
    vi.stubGlobal('fetch', vi.fn((_u: string, init: RequestInit) => new Promise((_r, reject) => {
      init.signal!.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
    })))
    const controller = new AbortController()
    const pending = explainJourney(search, direct, controller.signal)
    controller.abort()
    await expect(pending).rejects.toMatchObject({ message: 'Request cancelled.', retryable: false })
  })
})

// --- What the browser accepts and shows -----------------------------------------

const ok = {
  status: 'ok', ai_generated: true, model: 'openai/gpt-oss-20b',
  explanation: 'Board 17D at Colon.\nWaiting time is unknown.',
  notices: ['Built from documented data that is not field-verified.', '14B is flagged scarce: commuters report few trips.',
    'Total fare unavailable: at least one ride has no supported fare calculation.', 'Waiting time is unknown: no verified frequency data.'],
}

describe('reading the server answer', () => {
  it('shows the explanation as paragraphs with the AI model name', () => {
    expect(explanationFromResponse(ok)).toEqual({
      phase: 'ready', paragraphs: ['Board 17D at Colon.', 'Waiting time is unknown.'], notices: ok.notices, model: 'openai/gpt-oss-20b',
    })
  })

  it('passes the historic, scarce, unknown-fare and unknown-wait notices through unchanged', () => {
    const state = explanationFromResponse(ok)
    expect(state.phase === 'ready' && state.notices).toEqual(ok.notices)
  })

  it('refuses text that is not labelled AI-generated', () => {
    for (const body of [{ ...ok, ai_generated: false }, { ...ok, ai_generated: undefined }, { ...ok, ai_generated: 'true' }]) {
      expect(explanationFromResponse(body)).toMatchObject({ phase: 'unavailable', retryable: true })
    }
  })

  it.each([
    ['null', null], ['a string', 'hello'], ['an array', []], ['an empty object', {}],
    ['unknown status', { status: 'maybe' }],
    ['empty text', { ...ok, explanation: '   ' }],
    ['non-string text', { ...ok, explanation: 42 }],
    ['notices not a list', { ...ok, notices: 'warning' }],
    ['notices with non-strings', { ...ok, notices: [1] }],
    ['unavailable without a message', { status: 'unavailable', retryable: true }],
    ['unavailable without retryable', { status: 'unavailable', message: 'x' }],
  ])('treats malformed data (%s) as unavailable, never as an explanation', (_name, body) => {
    expect(parseExplainResponse(body)).toBeNull()
    expect(explanationFromResponse(body)).toEqual({
      phase: 'unavailable', message: 'The explanation is unavailable right now.', retryable: true,
    })
  })

  it('offers a retry when the AI provider timed out', () => {
    const body = { status: 'unavailable', reason: 'timeout', message: 'The AI service took too long to answer. Please try again.', retryable: true }
    expect(explanationFromResponse(body)).toEqual({ phase: 'unavailable', message: body.message, retryable: true })
  })

  it.each(['not_configured', 'quota'])('does not offer a retry when it is %s', (reason) => {
    const state = explanationFromResponse({ status: 'unavailable', reason, message: 'Not available.', retryable: false })
    expect(state).toEqual({ phase: 'unavailable', message: 'Not available.', retryable: false })
  })

  it('an answer that fails the server accuracy checks is unavailable, not shown', () => {
    const state = explanationFromResponse({ status: 'unavailable', reason: 'invalid_output', message: 'Did not pass checks.', retryable: true })
    expect(state).toMatchObject({ phase: 'unavailable' })
    expect(JSON.stringify(state)).not.toContain('explanation')
  })
})

describe('HTTP failures', () => {
  it('keeps the plain message and retryability of an API error', () => {
    expect(explanationFromError(new ApiError('You have searched a lot in a short time. Please wait a minute, then try again.', 429, true)))
      .toEqual({ phase: 'unavailable', message: 'You have searched a lot in a short time. Please wait a minute, then try again.', retryable: true })
  })

  it('does not offer a retry when the trip no longer exists', () => {
    expect(explanationFromError(new ApiError('That trip is no longer available. Please search again.', 404, false)))
      .toMatchObject({ phase: 'unavailable', retryable: false })
  })

  it('hides unexpected error details', () => {
    const state = explanationFromError(new TypeError('secret internal detail'))
    expect(state).toEqual({ phase: 'unavailable', message: 'The explanation is unavailable right now.', retryable: true })
  })

  it('maps real responses end to end (rate limit, trip changed, server down)', async () => {
    const cases: [number, object, boolean][] = [
      [429, { error: { message: 'Please wait a minute.', retryable: true } }, true],
      [404, { error: { message: 'That trip is no longer available. Please search again.', retryable: false } }, false],
      [503, { error: { message: 'Try later.', retryable: true } }, true],
    ]
    for (const [status, body, retryable] of cases) {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(body, status)))
      const error = await explainJourney(search, direct).catch((e: unknown) => e)
      expect(explanationFromError(error)).toMatchObject({ phase: 'unavailable', retryable })
    }
  })

  it('treats a network failure as retryable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const error = await explainJourney(search, direct).catch((e: unknown) => e)
    expect(explanationFromError(error)).toMatchObject({ phase: 'unavailable', retryable: true })
  })
})
