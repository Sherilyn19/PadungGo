// Labels for chosen places. A label never changes the coordinates used for
// planning: GPS and map points keep their exact values whatever address is found.
// Provider credits are shown once, in the map's (i) credits panel.
import type { AddressResponse, LatLng, Place, PlaceSuggestion, SuggestionsResponse } from './api'

export const GPS_PENDING_NAME = 'My location'
export const PIN_PENDING_NAME = 'Pinned on map'
export const ADDRESS_UNAVAILABLE = 'Selected location — address unavailable'

export function pendingPoint(point: LatLng, source: 'gps' | 'map'): Place {
  return {
    latitude: point.latitude,
    longitude: point.longitude,
    name: source === 'gps' ? GPS_PENDING_NAME : PIN_PENDING_NAME,
    source,
    addressStatus: 'pending',
  }
}

export function formatCoordinates(point: LatLng): string {
  return `${point.latitude.toFixed(5)}, ${point.longitude.toFixed(5)}`
}

export function samePoint(a: LatLng, b: LatLng): boolean {
  return a.latitude === b.latitude && a.longitude === b.longitude
}

/** Applies an address lookup result; anything but a resolved label becomes the fallback. */
export function withAddress(place: Place, response: AddressResponse | null): Place {
  const label = response?.status === 'resolved' ? response.label?.trim() : ''
  if (label) {
    return { ...place, name: label, addressStatus: 'resolved' }
  }
  return { ...place, name: ADDRESS_UNAVAILABLE, addressStatus: 'unavailable' }
}

/**
 * Labels `current` only if it is still the point that was looked up and still
 * waiting; a reply for an older or moved point is ignored.
 */
export function labelIfStillCurrent(current: Place | null, target: Place, response: AddressResponse | null): Place | null {
  const stillWaiting = current?.addressStatus === 'pending' && current.source === target.source && samePoint(current, target)
  return stillWaiting ? withAddress(current, response) : current
}

export function placeFromSuggestion(s: PlaceSuggestion): Place {
  if (s.source === 'padunggo' && s.location_id) {
    return { id: s.location_id, name: s.name, latitude: s.latitude, longitude: s.longitude, source: 'search' }
  }
  return {
    name: s.detail ? `${s.name}, ${s.detail}` : s.name,
    latitude: s.latitude,
    longitude: s.longitude,
    source: 'provider',
  }
}

export function suggestionKey(s: PlaceSuggestion): string {
  return s.location_id ?? `${s.source}:${s.latitude},${s.longitude}:${s.name}`
}

// Remembers recent suggestion lists so retyping or deleting a letter does not
// spend another provider request. Case and spacing are ignored.
const SUGGESTION_CACHE_SIZE = 40
const suggestionCache = new Map<string, SuggestionsResponse>()

export function suggestionCacheKey(query: string): string {
  return query.trim().toLowerCase().replace(/\s+/g, ' ')
}

export function cachedSuggestions(query: string): SuggestionsResponse | undefined {
  return suggestionCache.get(suggestionCacheKey(query))
}

export function rememberSuggestions(query: string, response: SuggestionsResponse): void {
  // Temporary provider problems are not cached, so a later try can succeed.
  if (!['ok', 'skipped', 'disabled'].includes(response.provider.status)) return
  const key = suggestionCacheKey(query)
  suggestionCache.delete(key)
  suggestionCache.set(key, response)
  if (suggestionCache.size > SUGGESTION_CACHE_SIZE) {
    suggestionCache.delete(suggestionCache.keys().next().value as string)
  }
}

export function clearSuggestionCache(): void {
  suggestionCache.clear()
}
