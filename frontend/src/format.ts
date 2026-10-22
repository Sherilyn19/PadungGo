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
  return m ? `${h} hr ${m} min` : `${h} hr`
}

export function formatDistance(meters: number | null | undefined): string {
  if (meters === null || meters === undefined) return 'Unknown'
  // Spelled out, so "224 m" is never mistaken for minutes.
  const rounded = Math.round(meters)
  if (rounded < 1000) return `${rounded} ${rounded === 1 ? 'meter' : 'meters'}`
  return `${(meters / 1000).toFixed(1)} km`
}

// A lower bound such as "547+ meters" or "1.2+ km" (walks are measured as
// straight lines, so the real path is at least this long).
export function formatMinimumDistance(meters: number): string {
  const [amount, unit] = formatDistance(meters).split(' ')
  return `${amount}+ ${unit}`
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
  return REASONS[reason] ?? 'We couldn’t find a trip. Try a nearby main road.'
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

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// "2026-10-18" -> "Oct 18, 2026". Parsed by hand so the browser's time zone
// can never shift the date by a day. Anything else returns null.
export function formatCalendarDate(value: string | null | undefined): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value ?? '')
  if (!match) return null
  const [, year, month, day] = match
  const monthIndex = Number(month) - 1
  if (monthIndex < 0 || monthIndex > 11 || Number(day) < 1 || Number(day) > 31) return null
  return `${MONTHS[monthIndex]} ${Number(day)}, ${year}`
}
