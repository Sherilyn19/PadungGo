// Turns a journey option into a commuter-friendly trip: a short name for the
// result card and an ordered timeline (start, walk, board, get off, transfer,
// arrive). Only facts from the API are used; uncertain ones get a short note
// in the main view and the longer explanation in an info tooltip.
import type { JourneyOption, RideSegment, Segment, TransferSegment } from './api'
import { fareDisplay, type FareDisplay } from './fareDisplay'
import { formatDistance, formatDuration, titleCase } from './format'

// Shared with the map so each ride's timeline colour matches its line.
export const RIDE_COLORS = ['#0078d7', '#062f57']

// Shorter walks are treated as "the stop is right here" and not listed as a step.
const MIN_LISTED_WALK_M = 15

export type TimelineKind = 'start' | 'walk' | 'board' | 'alight' | 'transfer' | 'arrive'

export interface TimelineStep {
  kind: TimelineKind
  title: string
  detail?: string
  note?: string
  // Longer explanation, shown behind an (i) icon.
  info?: string
  routeCode?: string
  routeName?: string
  fare?: FareDisplay
  color?: string
  // How the commuter travels from this step to the next one.
  connector: 'ride' | 'walk' | 'none'
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

export function tripName(option: JourneyOption): { from: string; to: string } {
  const legs = rides(option)
  if (legs.length === 0) return { from: 'Start', to: 'Destination' }
  return {
    from: stopName(legs[0].board_stop_name, 'Stop on map'),
    to: stopName(legs[legs.length - 1].alight_stop_name, 'Stop on map'),
  }
}

export function transferLabel(transfers: number): string {
  if (transfers === 0) return 'Direct'
  return transfers === 1 ? '1 transfer' : `${transfers} transfers`
}

export function rideColor(index: number): string {
  return RIDE_COLORS[index % RIDE_COLORS.length]
}

const STRAIGHT_LINE_INFO =
  'Measured in a straight line, so the street route will be a little longer. Follow the dotted line on the map.'

function walkStep(segment: Segment, toStopName: string | null): TimelineStep | null {
  const meters = 'straight_line_m' in segment ? segment.straight_line_m : null
  if (meters !== null && meters < MIN_LISTED_WALK_M) return null
  return {
    kind: 'walk',
    title: toStopName ? `Walk to ${stopName(toStopName)}` : 'Walk to your destination',
    detail: meters !== null ? `About ${formatDistance(meters)}` : undefined,
    info: STRAIGHT_LINE_INFO,
    connector: 'walk',
  }
}

function transferStep(segment: TransferSegment, next: RideSegment | undefined): TimelineStep {
  const nextCode = next?.route_code ?? 'your next jeepney'
  const sameStop = segment.from_stop_id !== undefined && segment.from_stop_id === segment.to_stop_id
  if (sameStop || segment.distance_m === 0) {
    return {
      kind: 'transfer',
      title: `Transfer to ${nextCode}`,
      detail: next ? `Wait at ${stopName(next.board_stop_name)}` : undefined,
      // Equal stop IDs don't prove the same street side, so don't say "stay put".
      note: `Check which side of the street ${nextCode} stops on.`,
      connector: 'walk',
    }
  }
  return {
    kind: 'transfer',
    title: `Transfer to ${nextCode}`,
    detail:
      segment.distance_m !== null
        ? `Walk about ${formatDistance(segment.distance_m)}${next ? ` to ${stopName(next.board_stop_name)}` : ''}`
        : next
          ? `Walk to ${stopName(next.board_stop_name)}`
          : undefined,
    info: 'The transfer path has not been checked on the ground.',
    connector: 'walk',
  }
}

function rideSteps(segment: RideSegment, color: string): [TimelineStep, TimelineStep] {
  const lookFor = segment.signboard
    ? `Look for the “${segment.signboard}” signboard`
    : `Look for ${segment.route_code} on the signboard`
  const stats =
    segment.distance_m !== null || segment.duration_seconds !== null
      ? [
          segment.distance_m !== null ? formatDistance(segment.distance_m) : null,
          segment.duration_seconds !== null ? `about ${formatDuration(segment.duration_seconds)} ride` : null,
        ]
          .filter(Boolean)
          .join(' · ')
      : undefined
  return [
    {
      kind: 'board',
      title: `Board at ${stopName(segment.board_stop_name)}`,
      detail: lookFor,
      note: stats,
      info: stats ? 'Ride time comes from older published schedules; traffic can change it.' : undefined,
      routeCode: segment.route_code,
      routeName: segment.route_name ? titleCase(segment.route_name) : undefined,
      fare: fareDisplay(segment.fare),
      color,
      connector: 'ride',
    },
    {
      kind: 'alight',
      title: `Get off at ${stopName(segment.alight_stop_name)}`,
      // "Lugar lang" is how Cebuano commuters ask the driver to stop.
      note: 'Say “Lugar lang” to the driver as you near the stop.',
      color,
      connector: 'walk',
    },
  ]
}

export function buildTimeline(option: JourneyOption, endpoints: TripEndpoints): TimelineStep[] {
  const steps: TimelineStep[] = [
    { kind: 'start', title: endpoints.originName, detail: 'Your starting point', connector: 'walk' },
  ]
  let rideIndex = 0
  option.segments.forEach((segment, index) => {
    if (segment.mode === 'ride') {
      steps.push(...rideSteps(segment, rideColor(rideIndex++)))
    } else if (segment.mode === 'transfer_walk') {
      const next = option.segments.slice(index + 1).find((s): s is RideSegment => s.mode === 'ride')
      steps.push(transferStep(segment, next))
    } else {
      const next = option.segments[index + 1]
      const step = walkStep(segment, next?.mode === 'ride' ? next.board_stop_name : null)
      if (step) steps.push(step)
    }
  })
  steps.push({ kind: 'arrive', title: endpoints.destinationName, detail: 'Your destination', connector: 'none' })
  return steps
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

// True when any ride comes from documented (historic) data rather than
// field-verified data. Drives the friendly "check locally" note.
export function needsLocalCheck(option: JourneyOption): boolean {
  return option.evidence.verification_status !== 'verified'
}
