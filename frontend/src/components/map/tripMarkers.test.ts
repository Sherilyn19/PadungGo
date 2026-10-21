import { describe, expect, it } from 'vitest'
import type { JourneyOption, RideSegment } from '../../api'
import { RIDE_COLORS } from '../../tripTimeline'
import { tripMarkers } from './tripMarkers'

const at = (latitude: number, longitude: number) => ({ latitude, longitude })

const ride = (code: string, start: [number, number], end: [number, number]): RideSegment =>
  ({
    mode: 'ride',
    route_code: code,
    board_stop_name: `${code} board`,
    alight_stop_name: 'Unnamed stop (feed id 9)',
    start: at(...start),
    end: at(...end),
  }) as RideSegment

const option = (...segments: RideSegment[]) => ({ segments }) as unknown as JourneyOption

describe('tripMarkers', () => {
  it('marks boarding and exit stops of a direct trip without feed IDs', () => {
    const markers = tripMarkers(option(ride('04I', [1, 1], [2, 2])))
    expect(markers.map((m) => [m.kind, m.label])).toEqual([
      ['board', 'Board 04I at 04I board'],
      ['alight', 'Get off 04I at this stop'],
    ])
  })

  it('shows one transfer marker when the next ride boards at the same point', () => {
    const markers = tripMarkers(option(ride('17C', [1, 1], [2, 2]), ride('51E', [2, 2], [3, 3])))
    expect(markers.map((m) => m.kind)).toEqual(['board', 'transfer', 'alight'])
    expect(markers.map((m) => m.color)).toEqual([RIDE_COLORS[0], RIDE_COLORS[1], RIDE_COLORS[1]])
  })

  it('keeps the exit marker when the transfer needs a walk', () => {
    const markers = tripMarkers(option(ride('17C', [1, 1], [2, 2]), ride('51E', [2.1, 2.1], [3, 3])))
    expect(markers.map((m) => m.kind)).toEqual(['board', 'alight', 'transfer', 'alight'])
  })

  it('draws nothing when no trip is selected', () => {
    expect(tripMarkers(null)).toEqual([])
  })
})
