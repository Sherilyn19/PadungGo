import { describe, expect, it } from 'vitest'
import type { GuideFareEstimate, JourneyOption, RideSegment } from '../api'
import { tripFareDisplay } from '../fareEstimates'
import { INITIAL_FARE_CHOICES, fareChoicesReducer, tripFareFor, vehicleChoicesFor } from './useFareChoices'

const SIX_KM: GuideFareEstimate = {
  status: 'available',
  reason: null,
  guide_effective_date: '2026-09-28',
  chargeable_km: 6,
  known_vehicle_type: null,
  amounts_centavos: { traditional: { regular: 1800, discounted: 1450 }, modern: { regular: 2175, discounted: 1750 } },
}

function ride(code: string): RideSegment {
  return {
    mode: 'ride', instruction: '', distance_m: 5900, duration_seconds: null, estimate_basis: null,
    route_id: code, route_code: code, route_name: code, signboard: null, vehicle_class: 'jeepney', operator: null,
    direction: 'unspecified', verification_status: 'documented', board_stop_name: 'A', alight_stop_name: 'B', geometry: null,
    fare: { amount_centavos: null, status: 'unavailable', reason: null },
    guide_fare_estimate: SIX_KM,
  }
}

const option = { id: 'trip-1', segments: [ride('A'), ride('B')] } as unknown as JourneyOption

// The screen re-renders from this state, so each change must give the new
// total straight away, without another request.
describe('fare choices update the fare immediately', () => {
  it('starts as Regular with Not sure for every ride', () => {
    expect(INITIAL_FARE_CHOICES.passenger).toBe('regular')
    expect(vehicleChoicesFor(INITIAL_FARE_CHOICES, option)).toEqual(['unsure', 'unsure'])
    expect(tripFareDisplay(tripFareFor(INITIAL_FARE_CHOICES, option)).amount).toBe('₱36.00–₱43.50')
  })

  it('recalculates when one ride changes, leaving the other ride alone', () => {
    const state = fareChoicesReducer(INITIAL_FARE_CHOICES, { type: 'vehicle', option, rideIndex: 1, vehicle: 'modern' })
    expect(vehicleChoicesFor(state, option)).toEqual(['unsure', 'modern'])
    expect(tripFareFor(state, option).total).toEqual({ low: 1800 + 2175, high: 2175 + 2175 })
  })

  it('recalculates every ride when the passenger type changes', () => {
    let state = fareChoicesReducer(INITIAL_FARE_CHOICES, { type: 'vehicle', option, rideIndex: 0, vehicle: 'traditional' })
    state = fareChoicesReducer(state, { type: 'vehicle', option, rideIndex: 1, vehicle: 'traditional' })
    state = fareChoicesReducer(state, { type: 'passenger', passenger: 'discounted' })
    expect(tripFareDisplay(tripFareFor(state, option)).text).toBe('₱29.00 Estimated')
  })

  it('keeps the passenger type but clears jeepney choices for a new search', () => {
    let state = fareChoicesReducer(INITIAL_FARE_CHOICES, { type: 'passenger', passenger: 'discounted' })
    state = fareChoicesReducer(state, { type: 'vehicle', option, rideIndex: 0, vehicle: 'modern' })
    state = fareChoicesReducer(state, { type: 'reset-vehicles' })
    expect(state).toEqual({ passenger: 'discounted', vehicles: {} })
  })

  it('ignores a ride index that does not exist', () => {
    expect(fareChoicesReducer(INITIAL_FARE_CHOICES, { type: 'vehicle', option, rideIndex: 5, vehicle: 'modern' })).toBe(INITIAL_FARE_CHOICES)
  })
})
