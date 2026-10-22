// Turns a journey option into a commuter-friendly trip: a short name for the
// result card and an ordered timeline (start, walk, board, ride, get off,
// transfer, arrive). Only facts from the API are used, in plain words.
import type { JourneyOption, RideSegment, Segment, TransferSegment } from './api'
import { formatDistance, formatDuration, titleCase } from './format'

// Ride colours: PadungGo blue first, then moss green and muted coral from the
// owner's cream/sage/coral reference, then charcoal, teal and plum. Every main
// colour passes 4.5:1 contrast with white text. Shared with the map so each
// ride's line matches its timeline.
export const RIDE_PALETTE = [
  { main: '#0078d7', soft: '#e6f1fb' },
  { main: '#4d7a35', soft: '#eef3e6' },
  { main: '#b5524c', soft: '#f9ecea' },
  { main: '#2f2f2f', soft: '#f1eee6' },
  { main: '#1a7778', soft: '#e2f2f1' },
  { main: '#7a5a8c', soft: '#f2edf5' },
] as const

export const RIDE_COLORS = RIDE_PALETTE.map((c) => c.main)

export function rideColor(index: number): string {
  return RIDE_PALETTE[index % RIDE_PALETTE.length].main
}

export function rideSoftColor(index: number): string {
  return RIDE_PALETTE[index % RIDE_PALETTE.length].soft
}

// Shorter walks are treated as "the stop is right here" and not listed as a step.
const MIN_LISTED_WALK_M = 15

export type TimelineKind = 'start' | 'walk' | 'board' | 'ride' | 'alight' | 'transfer' | 'arrive'

export interface TimelineStep {
  kind: TimelineKind
  title: string
  detail?: string
  // Set on board, ride and get-off steps; groups them into one coloured ride.
  rideIndex?: number
  routeCode?: string
  routeName?: string
}

export interface TripEndpoints {
  originName: string
  destinationName: string
}

export function rides(option: JourneyOption): RideSegment[] {
  return option.segments.filter((s): s is RideSegment => s.mode === 'ride')
}

// GTFS stops without a name are imported as "Unnamed stop (feed id …)". The ID
// means nothing to commuters, so point them at the map marker instead.
export function isUnnamedStop(name: string): boolean {
  return /^unnamed stop/i.test(name.trim())
}

export function stopName(name: string, fallback = 'the stop shown on the map'): string {
  return isUnnamedStop(name) ? fallback : name
}

// The Cebu DOTC feed uses "Name missing" as a placeholder route name, either
// alone ("Name missing") or after a place ("LABANGON (Name missing)"). Show
// only the real part; the route code always identifies the jeepney.
const NAME_PLACEHOLDER = /\(?\s*(name missing|no ?data)\s*\)?/gi

export function routeDisplayName(name: string | null | undefined, code: string): string | undefined {
  const cleaned = (name ?? '').replace(NAME_PLACEHOLDER, ' ').replace(/\s+/g, ' ').trim()
  if (!cleaned || cleaned.toLowerCase() === code.trim().toLowerCase()) return undefined
  return titleCase(cleaned)
}

export function tripName(option: JourneyOption): { from: string; to: string } {
  const legs = rides(option)
  if (legs.length === 0) return { from: 'Start', to: 'Destination' }
  return {
    from: stopName(legs[0].board_stop_name, 'Nearby stop'),
    to: stopName(legs[legs.length - 1].alight_stop_name, 'Nearby stop'),
  }
}

export function transferLabel(transfers: number): string {
  if (transfers === 0) return 'Direct'
  return transfers === 1 ? '1 transfer' : `${transfers} transfers`
}

function walkStep(segment: Segment, toStopName: string | null): TimelineStep | null {
  const meters = 'straight_line_m' in segment ? segment.straight_line_m : null
  if (meters !== null && meters < MIN_LISTED_WALK_M) return null
  return {
    kind: 'walk',
    title: toStopName ? `Walk to ${stopName(toStopName)}` : 'Walk to your destination',
    // Straight-line distance, so "at least" keeps it honest without a footnote.
    detail: meters !== null ? `At least ${formatDistance(meters)}` : undefined,
  }
}

function transferStep(segment: TransferSegment, next: RideSegment | undefined): TimelineStep {
  const nextCode = next?.route_code ?? 'your next jeepney'
  const sameStop = segment.from_stop_id !== undefined && segment.from_stop_id === segment.to_stop_id
  if (sameStop || segment.distance_m === 0) {
    return {
      kind: 'transfer',
      title: `Change to ${nextCode}`,
      // Equal stop IDs don't prove the same street side, so don't say "stay put".
      detail: `Check which side of the street ${nextCode} stops on.`,
    }
  }
  const to = next ? ` to ${stopName(next.board_stop_name)}` : ''
  return {
    kind: 'transfer',
    title: `Change to ${nextCode}`,
    detail: segment.distance_m !== null ? `Walk about ${formatDistance(segment.distance_m)}${to}` : `Walk${to}`,
  }
}

function rideStats(segment: RideSegment): string | undefined {
  const parts = [
    segment.distance_m !== null ? formatDistance(segment.distance_m) : null,
    segment.duration_seconds !== null ? `about ${formatDuration(segment.duration_seconds)}` : null,
  ].filter(Boolean)
  return parts.length ? parts.join(' · ') : undefined
}

function rideSteps(segment: RideSegment, rideIndex: number): TimelineStep[] {
  const shared = { rideIndex, routeCode: segment.route_code }
  return [
    {
      ...shared,
      kind: 'board',
      title: `Board at ${stopName(segment.board_stop_name)}`,
      detail: segment.signboard
        ? `Look for the “${segment.signboard}” signboard`
        : `Look for ${segment.route_code} on the signboard`,
      routeName: routeDisplayName(segment.route_name, segment.route_code),
    },
    // The ride block header already names the jeepney, so this row says how long.
    { ...shared, kind: 'ride', title: rideStats(segment) ? `Stay on for ${rideStats(segment)}` : `Stay on ${segment.route_code}` },
    {
      ...shared,
      kind: 'alight',
      title: `Get off at ${stopName(segment.alight_stop_name)}`,
      // Bisaya: "Almost there! Get ready to get off."
      detail: 'Hapit na! Andam na sa pagnaog.',
    },
  ]
}

export function buildTimeline(option: JourneyOption, endpoints: TripEndpoints): TimelineStep[] {
  const steps: TimelineStep[] = [{ kind: 'start', title: endpoints.originName }]
  let rideIndex = 0
  option.segments.forEach((segment, index) => {
    if (segment.mode === 'ride') {
      steps.push(...rideSteps(segment, rideIndex++))
    } else if (segment.mode === 'transfer_walk') {
      const next = option.segments.slice(index + 1).find((s): s is RideSegment => s.mode === 'ride')
      steps.push(transferStep(segment, next))
    } else {
      const next = option.segments[index + 1]
      const step = walkStep(segment, next?.mode === 'ride' ? next.board_stop_name : null)
      if (step) steps.push(step)
    }
  })
  steps.push({ kind: 'arrive', title: endpoints.destinationName })
  return steps
}

// Groups consecutive steps of the same ride, so each ride can be drawn as one
// coloured block with walks and transfers between them.
export type TimelineBlock =
  | { type: 'step'; step: TimelineStep }
  | { type: 'ride'; rideIndex: number; routeCode: string; routeName?: string; steps: TimelineStep[] }

export function groupTimeline(steps: TimelineStep[]): TimelineBlock[] {
  const blocks: TimelineBlock[] = []
  for (const step of steps) {
    const last = blocks.at(-1)
    if (step.rideIndex === undefined) blocks.push({ type: 'step', step })
    else if (last?.type === 'ride' && last.rideIndex === step.rideIndex) last.steps.push(step)
    else
      blocks.push({
        type: 'ride',
        rideIndex: step.rideIndex,
        routeCode: step.routeCode ?? '',
        routeName: step.routeName,
        steps: [step],
      })
  }
  return blocks
}

// Total straight-line walking, as a lower bound. Null when any walk is unmeasured.
export function straightLineWalkingMeters(option: JourneyOption): number | null {
  let total = 0
  for (const segment of option.segments) {
    if (segment.mode === 'walk') total += segment.straight_line_m
    else if (segment.mode === 'transfer_walk') {
      if (segment.distance_m === null) return null
      total += segment.distance_m
    }
  }
  return total
}

// True when any ride comes from older published data rather than field checks.
export function needsLocalCheck(option: JourneyOption): boolean {
  return option.evidence.verification_status !== 'verified'
}
