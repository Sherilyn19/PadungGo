import { describe, expect, it } from 'vitest'
import type { JourneyOption, RideSegment, Segment } from './api'
import { buildJourneySteps, RIDE_COLORS, straightLineWalkingMeters } from './journeySteps'

// Shaped like the production 17D → 42D demo response (values abridged).
const walk = (from: string, to: string, m: number): Segment => ({
  mode: 'walk',
  instruction: `Walk from ${from} to ${to} (approximate; not a verified route).`,
  distance_m: null,
  duration_seconds: null,
  estimate_basis: 'straight_line_approx',
  straight_line_m: m,
})

const ride = (code: string, board: string, alight: string, status = 'documented'): RideSegment => ({
  mode: 'ride',
  instruction: '',
  distance_m: 4055,
  duration_seconds: 644,
  estimate_basis: 'sourced_observation',
  route_id: 'r',
  route_code: code,
  route_name: '',
  signboard: null,
  vehicle_class: 'jeepney',
  operator: null,
  direction: 'unspecified',
  verification_status: status,
  board_stop_name: board,
  alight_stop_name: alight,
  geometry: null,
  fare: {
    amount_centavos: null,
    status: 'unavailable',
    reason: 'No supported fare calculation.',
  },
})

const transfer = (from: string, to: string, fromId: string, toId: string, m: number | null): Segment => ({
  mode: 'transfer_walk',
  instruction: `Transfer: walk from ${from} to ${to}.`,
  distance_m: m,
  duration_seconds: null,
  estimate_basis: null,
  from_stop_id: fromId,
  to_stop_id: toId,
})

function option(segments: Segment[]): JourneyOption {
  return { segments } as unknown as JourneyOption
}

const demo = option([
  walk('origin', 'Unnamed stop (feed id 2939)', 229),
  ride('17D', 'Unnamed stop (feed id 2939)', 'Sanciangko'),
  transfer('Sanciangko', 'Sanciangko', 'b059', 'b059', 0),
  ride('42D', 'Sanciangko', 'Cebu South Road'),
  walk('Cebu South Road', 'destination', 452.5),
])

describe('buildJourneySteps', () => {
  it('turns the demo journey into boarding, transfer and alighting steps', () => {
    const steps = buildJourneySteps(demo)
    expect(steps.map((s) => s.title)).toEqual([
      'Walk to Unnamed stop (feed id 2939)',
      'Board 17D at Unnamed stop (feed id 2939)',
      'Transfer to 42D at Sanciangko',
      'Board 42D at Sanciangko',
      'Walk to destination',
    ])
    expect(steps[1].details[0]).toBe('Get off at Sanciangko')
    expect(steps[3].details[0]).toBe('Get off at Cebu South Road')
  })

  it('never shows an unknown fare as a price, and keeps data caveats', () => {
    const [, firstRide, sameStop] = buildJourneySteps(demo)
    expect(firstRide.details).toContain('Fare unavailable')
    expect(firstRide.details).toContain('No supported fare calculation.')
    expect(firstRide.caveats[0]).toMatch(/Historic route data/)
    expect(sameStop.caveats[0]).toMatch(/same stop/)
  })

  it('colours rides like the map lines', () => {
    const steps = buildJourneySteps(demo).filter((s) => s.kind === 'ride')
    expect(steps.map((s) => s.color)).toEqual(RIDE_COLORS)
  })

  it('describes a transfer between different stops as a walk', () => {
    const steps = buildJourneySteps(option([transfer('Colon', 'Junquera', 'a', 'b', 120)]))
    expect(steps[0].title).toBe('Walk from Colon to Junquera.')
    expect(steps[0].details).toEqual(['About 120 m'])
  })

  it('drops the historic caveat for verified rides', () => {
    expect(buildJourneySteps(option([ride('01K', 'A', 'B', 'verified')]))[0].caveats).toEqual([])
  })
})

describe('straightLineWalkingMeters', () => {
  it('adds access, transfer and exit walks', () => {
    expect(straightLineWalkingMeters(demo)).toBe(681.5)
  })

  it('is unknown when a transfer distance is unknown', () => {
    expect(straightLineWalkingMeters(option([transfer('A', 'B', 'a', 'b', null)]))).toBeNull()
  })
})



describe('ride fare presentation', () => {
  it('shows an exact backend amount without an approximate label', () => {
    const segment = ride('TEST', 'Boarding stop', 'Exit stop', 'verified')
    segment.fare = {
      amount_centavos: 1950,
      status: 'exact',
      reason: null,
    }

    const [step] = buildJourneySteps(option([segment]))

    expect(step.details).toContain('₱19.50')
    expect(step.details.join(' ')).not.toContain('Approximate')
    expect(step.details.join(' ')).not.toContain('Fare unavailable')
  })

  it('shows an approximate amount together with its backend explanation', () => {
    const segment = ride('TEST', 'Boarding stop', 'Exit stop', 'verified')
    segment.fare = {
      amount_centavos: 1950,
      status: 'approximate',
      reason: 'Based on recorded ride distance; the billable distance may differ.',
    }

    const [step] = buildJourneySteps(option([segment]))

    expect(step.details).toContain('₱19.50 · Approximate')
    expect(step.details).toContain(
      'Based on recorded ride distance; the billable distance may differ.',
    )
    expect(step.details.join(' ')).not.toContain('Fare unavailable')
  })
})
