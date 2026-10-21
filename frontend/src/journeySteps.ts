// Turns a journey option into numbered, plain-language steps. Every step says
// which facts are known and which are approximate, so commuters can judge how
// far to trust it.
import type { JourneyOption, Segment } from './api'
import { formatDistance, formatDuration, formatFare } from './format'

// Shared with MapView so a step's colour matches its line on the map.
export const RIDE_COLORS = ['#059669', '#2563eb']

export type StepKind = 'walk' | 'ride' | 'transfer'

export interface JourneyStep {
  kind: StepKind
  title: string
  details: string[]
  // Caveats about data quality, shown in a muted style under the step.
  caveats: string[]
  color?: string
}

function walkStep(segment: Segment, isFirst: boolean): JourneyStep {
  const straightLine = 'straight_line_m' in segment ? segment.straight_line_m : null
  // The backend instruction reads "Walk from A to B (approximate; …)".
  const route = segment.instruction.replace(/^Walk from /, '').replace(/ \(approximate.*$/, '')
  const [from, to] = route.split(' to ')
  return {
    kind: 'walk',
    title: isFirst ? `Walk to ${to ?? 'the stop'}` : `Walk to ${to ?? 'your destination'}`,
    details: straightLine !== null ? [`About ${formatDistance(straightLine)} in a straight line from ${from ?? 'here'}`] : [],
    caveats: ['The real walking path is longer and not verified. Check the street route.'],
  }
}

function transferStep(segment: Extract<Segment, { mode: 'transfer_walk' }>, nextRoute: string | null): JourneyStep {
  const sameStop = segment.from_stop_id !== undefined && segment.from_stop_id === segment.to_stop_id
  const stopName = segment.instruction.replace(/^Transfer: walk from /, '').split(' to ')[0].replace(/\.$/, '')
  if (sameStop) {
    return {
      kind: 'transfer',
      title: `Stay at ${stopName} and wait for ${nextRoute ?? 'your next jeepney'}`,
      details: [],
      caveats: ['Both routes use the same stop in the data. Check which side of the street the next jeepney stops on.'],
    }
  }
  return {
    kind: 'transfer',
    title: segment.instruction.replace(/^Transfer: w/, 'W'),
    details: segment.distance_m !== null ? [`About ${formatDistance(segment.distance_m)}`] : [],
    caveats: ['Transfer path not verified.'],
  }
}

export function buildJourneySteps(option: JourneyOption): JourneyStep[] {
  const steps: JourneyStep[] = []
  let rideIndex = 0
  option.segments.forEach((segment, index) => {
    if (segment.mode === 'ride') {
      const details = [
        `Get off at ${segment.alight_stop_name}`,
        `${formatDistance(segment.distance_m)} · about ${formatDuration(segment.duration_seconds)} riding (old schedule)`,
      ]
      if (segment.signboard) details.push(`Signboard: “${segment.signboard}”`)
      details.push(`Fare: ${formatFare(segment.fare.amount_centavos)}`)
      steps.push({
        kind: 'ride',
        title: `Board ${segment.route_code} at ${segment.board_stop_name}`,
        details,
        caveats: segment.verification_status === 'verified' ? [] : ['Historic route data: confirm with the driver or signboard.'],
        color: RIDE_COLORS[rideIndex++ % RIDE_COLORS.length],
      })
    } else if (segment.mode === 'transfer_walk') {
      const next = option.segments.slice(index + 1).find((s) => s.mode === 'ride')
      steps.push(transferStep(segment, next && next.mode === 'ride' ? next.route_code : null))
    } else {
      steps.push(walkStep(segment, index === 0))
    }
  })
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
