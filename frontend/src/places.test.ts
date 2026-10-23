import { afterEach, describe, expect, it, vi } from 'vitest'
import { suggestPlaces, type AddressResponse, type PlaceSuggestion, type SuggestionsResponse } from './api'
import {
  ADDRESS_UNAVAILABLE,
  cachedSuggestions,
  clearSuggestionCache,
  formatCoordinates,
  labelIfStillCurrent,
  pendingPoint,
  placeFromSuggestion,
  rememberSuggestions,
  suggestionAttribution,
} from './places'

// Synthetic test-only coordinates.
const PIN = { latitude: 10.300123, longitude: 123.901234 }

function reply(overrides: Partial<AddressResponse> = {}): AddressResponse {
  return {
    status: 'resolved',
    label: 'Osmeña Boulevard, Cebu City',
    latitude: 10.3002,
    longitude: 123.9013,
    distance_m: 12,
    reason: null,
    attribution: [{ text: 'Powered by Geoapify', url: 'https://www.geoapify.com/' }],
    ...overrides,
  }
}

describe('address labels', () => {
  it('shows a resolved address but keeps the exact point', () => {
    const pin = pendingPoint(PIN, 'map')
    const labelled = labelIfStillCurrent(pin, pin, reply())

    expect(labelled).toMatchObject({ name: 'Osmeña Boulevard, Cebu City', addressStatus: 'resolved', ...PIN })
  })

  it.each([
    reply({ status: 'no_result', label: null }),
    reply({ status: 'unavailable', label: null, reason: 'quota' }),
    null,
  ])('falls back without inventing an address', (response) => {
    const gps = pendingPoint(PIN, 'gps')
    expect(labelIfStillCurrent(gps, gps, response)).toMatchObject({
      name: ADDRESS_UNAVAILABLE,
      addressStatus: 'unavailable',
      ...PIN,
    })
  })

  it('ignores a reply for a pin the user has since moved', () => {
    const oldPin = pendingPoint(PIN, 'map')
    const newPin = pendingPoint({ latitude: 10.31, longitude: 123.91 }, 'map')

    expect(labelIfStillCurrent(newPin, oldPin, reply())).toBe(newPin)
    expect(labelIfStillCurrent(null, oldPin, reply())).toBeNull()
  })

  it('formats coordinates for display', () => {
    expect(formatCoordinates(PIN)).toBe('10.30012, 123.90123')
  })
})

const curated: PlaceSuggestion = {
  source: 'padunggo', location_id: 'loc-1', name: 'Example Campus', detail: 'Cebu City',
  kind: 'school', latitude: 10.3, longitude: 123.9, status: 'candidate',
}
const mapResult: PlaceSuggestion = {
  source: 'geoapify', location_id: null, name: 'Example Bakery', detail: 'Colon Street, Cebu City',
  kind: 'business', latitude: 10.29, longitude: 123.9,
  data_attribution: { text: '© OpenStreetMap contributors', url: 'https://www.openstreetmap.org/copyright' },
}

describe('suggestions', () => {
  afterEach(() => {
    clearSuggestionCache()
    vi.unstubAllGlobals()
  })

  it('falls back to the older locations endpoint while the backend is not yet updated', async () => {
    const json = (status: number, body: unknown) =>
      new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(json(404, { error: { code: 'not_found', message: 'Not found.' } }))
      .mockResolvedValueOnce(json(200, { results: [
        { id: 'loc-1', name: 'Fuente Osmeña', kind: 'place', area: null, status: 'documented', latitude: 10.31, longitude: 123.89 },
      ] }))
    vi.stubGlobal('fetch', fetchMock)

    const data = await suggestPlaces('osmena')

    expect(fetchMock.mock.calls[1][0]).toContain('/locations?q=osmena')
    expect(data.results[0]).toMatchObject({ source: 'padunggo', location_id: 'loc-1', name: 'Fuente Osmeña' })
  })

  it('plans PadungGo locations by id and map results by coordinates', () => {
    expect(placeFromSuggestion(curated)).toEqual({
      id: 'loc-1', name: 'Example Campus', latitude: 10.3, longitude: 123.9, source: 'search',
    })
    const place = placeFromSuggestion(mapResult)
    expect(place.id).toBeUndefined()
    expect(place).toMatchObject({ name: 'Example Bakery, Colon Street, Cebu City', source: 'provider' })
    expect(place.attribution?.map((a) => a.text)).toEqual(['Powered by Geoapify', '© OpenStreetMap contributors'])
  })

  it('credits the provider only when its results are shown', () => {
    expect(suggestionAttribution([curated])).toEqual([])
    expect(suggestionAttribution([curated, mapResult, mapResult]).map((a) => a.text)).toEqual([
      'Powered by Geoapify',
      '© OpenStreetMap contributors',
    ])
  })

  it('reuses results regardless of case and skips temporary failures', () => {
    const ok: SuggestionsResponse = { results: [curated], provider: { name: 'geoapify', status: 'ok', attribution: [] } }
    rememberSuggestions('CTU ', ok)
    expect(cachedSuggestions('ctu')).toBe(ok)

    const failed = { ...ok, provider: { ...ok.provider, status: 'timeout' } }
    rememberSuggestions('ayala', failed)
    expect(cachedSuggestions('ayala')).toBeUndefined()
  })
})
