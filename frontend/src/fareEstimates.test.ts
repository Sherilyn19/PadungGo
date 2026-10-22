import { describe, expect, it } from 'vitest'
import type { GuideFareEstimate, JourneyOption, RideSegment } from './api'
import {
  defaultVehicleChoice,
  fareColumn,
  rideFare,
  rideFareDisplay,
  tripFare,
  tripFareDisplay,
} from './fareEstimates'

// Literal amounts from docs/FARE_GUIDE_2026-09-28.md (new-fare columns), as
// the backend sends them. The frontend must pick these, never recompute them.
const GUIDE = {
  2: { traditional: { regular: 1400, discounted: 1125 }, modern: { regular: 1700, discounted: 1350 } },
  6: { traditional: { regular: 1800, discounted: 1450 }, modern: { regular: 2175, discounted: 1750 } },
  10: { traditional: { regular: 2600, discounted: 2075 }, modern: { regular: 3150, discounted: 2500 } },
} as const

function estimate(km: keyof typeof GUIDE, known: GuideFareEstimate['known_vehicle_type'] = null): GuideFareEstimate {
  return {
    status: 'available',
    reason: null,
    guide_effective_date: '2026-09-28',
    chargeable_km: km,
    known_vehicle_type: known,
    amounts_centavos: structuredClone(GUIDE[km]) as GuideFareEstimate['amounts_centavos'],
  }
}

function ride(code: string, guide: GuideFareEstimate | null | undefined, fare?: Partial<RideSegment['fare']>): RideSegment {
  return {
    mode: 'ride',
    instruction: '',
    distance_m: 5900,
    duration_seconds: null,
    estimate_basis: null,
    route_id: code,
    route_code: code,
    route_name: code,
    signboard: null,
    vehicle_class: 'jeepney',
    operator: null,
    direction: 'unspecified',
    verification_status: 'documented',
    board_stop_name: 'A',
    alight_stop_name: 'B',
    geometry: null,
    fare: { amount_centavos: null, status: 'unavailable', reason: 'No supported fare calculation.', ...fare },
    guide_fare_estimate: guide,
  }
}

function trip(...legs: RideSegment[]): JourneyOption {
  return {
    id: 'trip',
    transfers: legs.length - 1,
    labels: [],
    segments: legs,
    fare: { currency: 'PHP', total_centavos: null, known_subtotal_centavos: 0, total_is_complete: false, status: 'unavailable', reason: null },
    time: { walking_seconds: null, waiting_seconds: null, riding_seconds: null, total_seconds: null, known_subtotal_seconds: 0, total_is_complete: false, uncertainty_notes: [] },
    evidence: { verification_status: 'documented', references: [] },
    warnings: [],
  }
}

describe('passenger fare column', () => {
  it('maps the grouped Student · Senior · PWD choice to the guide discounted column', () => {
    expect(fareColumn('regular')).toBe('regular')
    expect(fareColumn('discounted')).toBe('discounted')
  })
})

describe('rideFare from guide estimates', () => {
  const six = ride('17D', estimate(6))

  it('picks the traditional and modern regular fares', () => {
    expect(rideFareDisplay(rideFare(six, 'traditional', 'regular')).text).toBe('₱18.00 Estimated')
    expect(rideFareDisplay(rideFare(six, 'modern', 'regular')).text).toBe('₱21.75 Estimated')
  })

  it('shows the traditional-to-modern range when the type is not known', () => {
    const fare = rideFare(six, 'unsure', 'regular')
    expect([fare.low, fare.high]).toEqual([1800, 2175])
    expect(rideFareDisplay(fare).text).toBe('₱18.00–₱21.75 Estimated')
  })

  it('uses the printed discounted amounts, not a percentage of the regular fare', () => {
    expect(rideFare(six, 'traditional', 'discounted').low).toBe(1450)
    expect(rideFare(six, 'modern', 'discounted').low).toBe(1750)
    expect(rideFareDisplay(rideFare(six, 'unsure', 'discounted')).text).toBe('₱14.50–₱17.50 Estimated')
    // 80% of ₱21.75 would be ₱17.40; the guide prints ₱17.50.
    expect(rideFare(six, 'modern', 'discounted').low).not.toBe(1740)
  })

  it('always labels guide amounts Estimated and allows choosing the jeepney type', () => {
    const fare = rideFare(six, 'traditional', 'regular')
    expect(fare).toMatchObject({ basis: 'estimate', estimated: true, vehicleSelectable: true })
  })

  it('formats every amount with exactly two decimals', () => {
    const ten = ride('X', estimate(10))
    expect(rideFareDisplay(rideFare(ten, 'traditional', 'discounted')).amount).toBe('₱20.75')
    expect(rideFareDisplay(rideFare(ten, 'modern', 'discounted')).amount).toBe('₱25.00')
  })
})

describe('rides without a defensible fare', () => {
  it('asks the driver when the backend has no estimate (older backend)', () => {
    const fare = rideFare(ride('X', undefined), 'unsure', 'regular')
    expect(fare.basis).toBe('none')
    expect(rideFareDisplay(fare).text).toBe('Ask the driver')
  })

  it('asks the driver beyond the guide range or with a missing distance', () => {
    for (const reason of ['beyond_guide_range', 'missing_distance']) {
      const unavailable: GuideFareEstimate = { ...estimate(6), status: 'unavailable', reason, chargeable_km: null, amounts_centavos: null }
      expect(rideFare(ride('X', unavailable), 'traditional', 'regular').low).toBeNull()
    }
  })

  it('rejects malformed amounts instead of showing them', () => {
    const bad = estimate(6)
    bad.amounts_centavos!.modern.regular = 21.75
    expect(rideFare(ride('X', bad), 'modern', 'regular').basis).toBe('none')
    const negative = estimate(6)
    negative.amounts_centavos!.traditional.discounted = -1
    expect(rideFare(ride('X', negative), 'traditional', 'discounted').basis).toBe('none')
  })
})

describe('verified fares', () => {
  const verified = ride('V', estimate(6, 'traditional'), { amount_centavos: 1500, status: 'exact', reason: null, rule_id: 'r1', passenger_category: 'regular' })

  it('keep priority over guide estimates, without a label or jeepney picker', () => {
    const fare = rideFare(verified, 'modern', 'regular')
    expect(fare).toMatchObject({ low: 1500, high: 1500, basis: 'verified', estimated: false, vehicleSelectable: false })
    expect(rideFareDisplay(fare).text).toBe('₱15.00')
  })

  it('are never reused for another passenger category', () => {
    expect(rideFare(verified, 'traditional', 'discounted').basis).toBe('none')
  })

  it('stay Estimated when the backend classed them approximate', () => {
    const approx = ride('V', null, { amount_centavos: 1950, status: 'approximate', reason: 'x', rule_id: 'r2' })
    expect(rideFareDisplay(rideFare(approx, 'unsure', 'regular')).text).toBe('₱19.50 Estimated')
  })
})

describe('default jeepney type', () => {
  it('is Not sure unless verified evidence names the type', () => {
    expect(defaultVehicleChoice(ride('X', estimate(6)))).toBe('unsure')
    expect(defaultVehicleChoice(ride('X', estimate(6, 'modern')))).toBe('modern')
    expect(defaultVehicleChoice(ride('X', undefined))).toBe('unsure')
  })
})

describe('tripFare totals', () => {
  const r1 = ride('01K', estimate(6))
  const r2 = ride('62B', estimate(2))
  const r3 = ride('17D', estimate(10))

  it('prices each ride on its own choices for a mixed three-ride trip', () => {
    const fare = tripFare(trip(r1, r2, r3), ['traditional', 'modern', 'traditional'], 'regular')
    // ₱18.00 + ₱17.00 + ₱26.00
    expect(fare.total).toEqual({ low: 6100, high: 6100 })
    expect(tripFareDisplay(fare).text).toBe('₱61.00 Estimated')
  })

  it('adds lows and highs separately when rides are uncertain', () => {
    const fare = tripFare(trip(r1, r2, r3), ['unsure', 'traditional', 'unsure'], 'regular')
    // Low ₱18.00 + ₱14.00 + ₱26.00; high ₱21.75 + ₱14.00 + ₱31.50
    expect(fare.total).toEqual({ low: 5800, high: 6725 })
    expect(tripFareDisplay(fare).text).toBe('₱58.00–₱67.25 Estimated')
  })

  it('applies one passenger type to every ride', () => {
    const fare = tripFare(trip(r1, r2), ['modern', 'modern'], 'discounted')
    expect(fare.total).toEqual({ low: 1750 + 1350, high: 1750 + 1350 })
  })

  it('shows no total when any ride lacks a fare', () => {
    const fare = tripFare(trip(r1, ride('X', undefined)), ['traditional', 'unsure'], 'regular')
    expect(fare.total).toBeNull()
    expect(fare.rides[0].low).toBe(1800)
    expect(tripFareDisplay(fare).text).toBe('Ask the driver')
  })

  it('shows a plain total when every ride is verified exact', () => {
    const v = ride('V', null, { amount_centavos: 1500, status: 'exact', reason: null, rule_id: 'r' })
    expect(tripFareDisplay(tripFare(trip(v, v), [], 'regular')).text).toBe('₱30.00')
  })

  it('uses defaults for rides without a saved choice', () => {
    expect(tripFare(trip(r1), [], 'regular').total).toEqual({ low: 1800, high: 2175 })
  })
})
