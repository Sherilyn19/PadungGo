import type { CoverageHint } from './api'
import { formatDistance } from './format'

export interface NoTripMessage {
  // Short, friendly, plain words.
  text: string
  // True when the same two places are worth trying the other way round.
  suggestReverse: boolean
}

// Distances under this are close enough that "far" would be wrong.
const FAR_METERS = 1500

function which(coverage: CoverageHint): 'start' | 'destination' | 'both' | null {
  if (!coverage.origin_has_stop && !coverage.destination_has_stop) return 'both'
  if (!coverage.origin_has_stop) return 'start'
  if (!coverage.destination_has_stop) return 'destination'
  return null
}

function distanceNote(meters: number | null): string {
  if (meters === null) return ''
  return meters >= FAR_METERS ? ` The closest one we know is about ${formatDistance(meters)} away.` : ''
}

// Explains an empty result using what the server found out. Falls back to the
// plain reason text when the server sent no details (older backends).
export function noTripMessage(reason: string | null, coverage: CoverageHint | null | undefined, fallback: string): NoTripMessage {
  if (reason === 'insufficient_verified_data' && coverage) {
    const side = which(coverage)
    if (side === 'both') {
      return {
        text: 'We don’t have jeepney stops near your start or your destination yet. Our map of routes is still growing.',
        suggestReverse: false,
      }
    }
    if (side === 'destination') {
      return {
        text: `We don’t have jeepney stops near your destination yet.${distanceNote(coverage.nearest_destination_stop_m)} Try a place nearer a main road.`,
        suggestReverse: false,
      }
    }
    if (side === 'start') {
      return {
        text: `We don’t have jeepney stops near your start yet.${distanceNote(coverage.nearest_origin_stop_m)} Try a place nearer a main road.`,
        suggestReverse: false,
      }
    }
  }
  if (reason === 'no_journey_within_mvp_limits' && coverage?.reverse_has_trips) {
    return {
      text: 'We found jeepney stops at both ends, but no trip in this direction yet. The trip back works, so some routes may only be recorded one way.',
      suggestReverse: true,
    }
  }
  return { text: fallback, suggestReverse: reason === 'no_journey_within_mvp_limits' }
}
