import { describe, expect, it } from 'vitest'
import type { JourneyOption, RideSegment, Segment } from './api'
import {
  buildTimeline,
  groupTimeline,
  RIDE_COLORS,
  straightLineWalkingMeters,
  stopName,
  transferLabel,
  tripName,
} from './tripTimeline'

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
  route_name: 'PLAZA HOUSING - LAHUG - CARBON',
  signboard: null,
  vehicle_class: 'jeepney',
  operator: null,
  direction: 'unspecified',
  verification_status: status,
  board_stop_name: board,
  alight_stop_name: alight,
  geometry: null,
  fare: { amount_centavos: null, status: 'unavailable', reason: 'No supported fare calculation.' },
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

function option(segments: Segment[], transfers = 0): JourneyOption {
  return { segments, transfers, evidence: { verification_status: 'documented', references: [] } } as unknown as JourneyOption
}

const ends = { originName: 'Ayala Center', destinationName: 'Colon' }

const demo = option(
  [
    walk('origin', 'Unnamed stop (feed id 2939)', 229),
    ride('17D', 'Unnamed stop (feed id 2939)', 'Sanciangko'),
    transfer('Sanciangko', 'Sanciangko', 'b059', 'b059', 0),
    ride('42D', 'Sanciangko', 'Cebu South Road'),
    walk('Cebu South Road', 'destination', 452.5),
  ],
  1,
)

describe('tripName', () => {
  it('names the trip from first boarding stop to last exit, hiding feed IDs', () => {
    expect(tripName(demo)).toEqual({ from: 'Nearby stop', to: 'Cebu South Road' })
    expect(tripName(option([ride('04I', 'Jakosalem Street', 'Colon & A. Borromeo')]))).toEqual({
      from: 'Jakosalem Street',
      to: 'Colon & A. Borromeo',
    })
  })

  it('labels transfer counts concisely', () => {
    expect([0, 1, 2].map(transferLabel)).toEqual(['Direct', '1 transfer', '2 transfers'])
  })

  it('never exposes "Unnamed stop (feed id …)" text', () => {
    expect(stopName('Unnamed stop (feed id 273)')).toBe('the stop shown on the map')
    expect(stopName('Osmeña Boulevard')).toBe('Osmeña Boulevard')
  })
})

describe('buildTimeline', () => {
  it('turns the demo journey into start, walk, board, ride, get off, transfer and arrive steps', () => {
    const steps = buildTimeline(demo, ends)
    expect(steps.map((s) => [s.kind, s.title])).toEqual([
      ['start', 'Ayala Center'],
      ['walk', 'Walk to the stop shown on the map'],
      ['board', 'Board at the stop shown on the map'],
      ['ride', 'Stay on for 4.1 km · about 11 min'],
      ['alight', 'Get off at Sanciangko'],
      ['transfer', 'Change to 42D'],
      ['board', 'Board at Sanciangko'],
      ['ride', 'Stay on for 4.1 km · about 11 min'],
      ['alight', 'Get off at Cebu South Road'],
      ['walk', 'Walk to your destination'],
      ['arrive', 'Colon'],
    ])
    expect(steps.every((s) => !/feed id/i.test(JSON.stringify(s)))).toBe(true)
  })

  it('keeps the same-stop street-side caveat for transfers', () => {
    const transferStep = buildTimeline(demo, ends).find((s) => s.kind === 'transfer')!
    expect(transferStep.detail).toMatch(/which side of the street 42D/)
  })

  it('describes a transfer between different stops as a walk', () => {
    const steps = buildTimeline(
      option([ride('01K', 'A', 'Colon'), transfer('Colon', 'Junquera', 'a', 'b', 120), ride('02B', 'Junquera', 'C')]),
      ends,
    )
    expect(steps.find((s) => s.kind === 'transfer')!.detail).toBe('Walk about 120 m to Junquera')
  })

  it('skips negligible walks instead of listing a 0 m step', () => {
    const steps = buildTimeline(option([walk('origin', 'A', 3), ride('04I', 'A', 'B'), walk('B', 'destination', 0)]), ends)
    expect(steps.map((s) => s.kind)).toEqual(['start', 'board', 'ride', 'alight', 'arrive'])
  })

  it('groups each ride into one block, numbered for the colour palette', () => {
    const blocks = groupTimeline(buildTimeline(demo, ends))
    expect(blocks.map((b) => (b.type === 'ride' ? `ride${b.rideIndex}:${b.routeCode}:${b.steps.length}` : b.step.kind))).toEqual([
      'start',
      'walk',
      'ride0:17D:3',
      'transfer',
      'ride1:42D:3',
      'walk',
      'arrive',
    ])
    expect(new Set(RIDE_COLORS).size).toBe(RIDE_COLORS.length)
  })

  it('shows the route code, a readable route name and ride stats', () => {
    const board = buildTimeline(demo, ends).find((s) => s.kind === 'board')!
    expect(board.routeCode).toBe('17D')
    expect(board.routeName).toBe('Plaza Housing - Lahug - Carbon')
    expect(board.detail).toBe('Look for 17D on the signboard')
    const ride = buildTimeline(demo, ends).find((s) => s.kind === 'ride')!
    expect(ride.title).toBe('Stay on for 4.1 km · about 11 min')
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
