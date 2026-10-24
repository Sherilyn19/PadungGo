import { describe, expect, it } from 'vitest'
import type { CoverageHint } from './api'
import { noTripMessage } from './noTripMessage'

const FALLBACK = 'We couldn’t find a trip.'
const hint = (over: Partial<CoverageHint> = {}): CoverageHint => ({
  search_radius_m: 500, origin_has_stop: true, destination_has_stop: true,
  nearest_origin_stop_m: 100, nearest_destination_stop_m: 100, reverse_has_trips: null, ...over,
})

describe('no-trip message', () => {
  it('names the destination when it has no stop, with how far the nearest one is', () => {
    const m = noTripMessage('insufficient_verified_data', hint({ destination_has_stop: false, nearest_destination_stop_m: 5200 }), FALLBACK)
    expect(m.text).toContain('near your destination')
    expect(m.text).toContain('5.2 km')
    expect(m.suggestReverse).toBe(false)
  })

  it('names the start when it has no stop', () => {
    const m = noTripMessage('insufficient_verified_data', hint({ origin_has_stop: false, nearest_origin_stop_m: 3000 }), FALLBACK)
    expect(m.text).toContain('near your start')
    expect(m.text).not.toContain('destination')
  })

  it('says so when neither end has a stop', () => {
    const m = noTripMessage('insufficient_verified_data', hint({ origin_has_stop: false, destination_has_stop: false }), FALLBACK)
    expect(m.text).toContain('start or your destination')
  })

  it('does not call a nearby stop far away (no distance under 1.5 km)', () => {
    const m = noTripMessage('insufficient_verified_data', hint({ destination_has_stop: false, nearest_destination_stop_m: 800 }), FALLBACK)
    expect(m.text).not.toMatch(/closest one we know/)
  })

  it('leaves out the distance when none is known', () => {
    const m = noTripMessage('insufficient_verified_data', hint({ destination_has_stop: false, nearest_destination_stop_m: null }), FALLBACK)
    expect(m.text).not.toMatch(/closest one we know/)
  })

  it('points to the trip back when only the other direction has trips', () => {
    const m = noTripMessage('no_journey_within_mvp_limits', hint({ reverse_has_trips: true }), FALLBACK)
    expect(m.suggestReverse).toBe(true)
    expect(m.text).toContain('trip back works')
  })

  it('keeps the plain text when the other direction has no trips either', () => {
    const m = noTripMessage('no_journey_within_mvp_limits', hint({ reverse_has_trips: false }), FALLBACK)
    expect(m.text).toBe(FALLBACK)
  })

  it('still offers the trip back on older backends that send no details', () => {
    expect(noTripMessage('no_journey_within_mvp_limits', undefined, FALLBACK)).toEqual({ text: FALLBACK, suggestReverse: true })
    expect(noTripMessage('insufficient_verified_data', null, FALLBACK)).toEqual({ text: FALLBACK, suggestReverse: false })
  })

  it('uses the plain text for other reasons', () => {
    expect(noTripMessage('same_location', hint(), FALLBACK)).toEqual({ text: FALLBACK, suggestReverse: false })
  })
})
