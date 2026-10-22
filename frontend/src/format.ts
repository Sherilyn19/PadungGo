// Display helpers. Unknown values are shown as unknown, never as zero.

// Formats whole centavos with integer maths, so no floating-point rounding
// can change a displayed amount (e.g. 1825 -> "₱18.25").
export function formatFare(centavos: number | null | undefined): string {
  if (centavos === null || centavos === undefined || !Number.isSafeInteger(centavos) || centavos < 0) return 'Unknown'
  const pesos = Math.floor(centavos / 100)
  const cents = String(centavos % 100).padStart(2, '0')
  return `₱${pesos}.${cents}`
}

// "₱18.00" when both ends match, otherwise "₱18.00–₱21.75".
export function formatFareRange(lowCentavos: number, highCentavos: number): string {
  return lowCentavos === highCentavos
    ? formatFare(lowCentavos)
    : `${formatFare(lowCentavos)}–${formatFare(highCentavos)}`
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return 'Unknown'
  const minutes = Math.max(1, Math.round(seconds / 60))
  if (minutes < 60) return `${minutes} min`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `${h} h ${m} min` : `${h} h`
}

export function formatDistance(meters: number | null | undefined): string {
  if (meters === null || meters === undefined) return 'Unknown'
  if (meters < 1000) return `${Math.round(meters)} m`
  return `${(meters / 1000).toFixed(1)} km`
}

const REASONS: Record<string, string> = {
  same_location: 'Your start and destination are the same place.',
  insufficient_verified_data:
    'We don’t know a jeepney stop close to your start or destination yet. Try a point nearer a main road.',
  no_journey_within_mvp_limits:
    'We couldn’t find a jeepney trip between these places with at most one transfer. Try a nearby main road, or check the trip back — some routes only run one way.',
  outside_intended_area: 'This place is outside Cebu City, Mandaue City and Lapu-Lapu City.',
}

export function explainReason(reason: string | null): string {
  if (!reason) return ''
  return REASONS[reason] ?? 'No journey was found for this request.'
}

export function titleCase(text: string): string {
  return text
    .toLowerCase()
    .replace(/(^|[\s(\-/])([a-zñ])/g, (_m, sep: string, ch: string) => sep + ch.toUpperCase())
}

const SORT_NAMES: Record<string, string> = {
  fewest_transfers: 'fewest transfers',
  cheapest: 'cheapest',
  fastest: 'fastest',
  least_walking: 'least walking',
}

// One short line when the backend could not use the requested order.
export function explainRanking(ranking: { requested: string; applied: string; warning: string | null }): string | null {
  if (!ranking.warning || ranking.requested === ranking.applied) return null
  const applied = SORT_NAMES[ranking.applied] ?? ranking.applied
  const requested = SORT_NAMES[ranking.requested] ?? ranking.requested
  return `Can’t sort by ${requested} yet, so trips are shown by ${applied}.`
}
