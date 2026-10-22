// Combines each ride's fare with the commuter's choices (passenger type and
// jeepney type) into ride and trip fares. The backend computes every amount
// from the LTFRB fare guides; this module only picks and adds whole centavos,
// so it never calculates or rounds a fare itself.
import type { GuideFareColumn, GuideFareEstimate, GuideVehicleType, JourneyOption, RideSegment } from './api'
import type { FareDisplay } from './fareDisplay'
import { formatFareRange } from './format'
import { rides } from './tripTimeline'

export type VehicleChoice = GuideVehicleType | 'unsure'
// Student, senior and PWD share one choice: both guides print a single
// "Student / Elderly / PWD" column with identical amounts.
export type PassengerType = GuideFareColumn

export const PASSENGER_TYPES: { value: PassengerType; label: string }[] = [
  { value: 'regular', label: 'Regular' },
  { value: 'discounted', label: 'Student · Senior · PWD' },
]

export const VEHICLE_CHOICES: { value: VehicleChoice; label: string }[] = [
  { value: 'traditional', label: 'Traditional' },
  { value: 'modern', label: 'Modern' },
  { value: 'unsure', label: 'Not sure' },
]

export const DEFAULT_PASSENGER: PassengerType = 'regular'

// Uses the guide's own discounted amounts, never a percentage of the regular fare.
export function fareColumn(passenger: PassengerType): GuideFareColumn {
  return passenger
}

export interface RideFare {
  // Lowest and highest possible fare in centavos. Equal when only one applies;
  // both null when there is no fare we can stand behind.
  low: number | null
  high: number | null
  basis: 'verified' | 'estimate' | 'none'
  estimated: boolean
  // Only guide estimates depend on the jeepney type the commuter picks.
  vehicleSelectable: boolean
}

export interface TripFare {
  rides: RideFare[]
  // Null unless every ride has a fare, so a partial sum is never shown as a total.
  total: { low: number; high: number } | null
  estimated: boolean
}

const NO_FARE: RideFare = { low: null, high: null, basis: 'none', estimated: false, vehicleSelectable: false }

function isCentavos(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
}

// A verified quote exists when the backend matched an admin-verified fare rule.
function hasVerifiedQuote(segment: RideSegment): boolean {
  return segment.fare.status === 'exact' || segment.fare.status === 'approximate'
}

function verifiedFare(segment: RideSegment, passenger: PassengerType): RideFare {
  const { fare } = segment
  // A verified quote is for one passenger category; never reuse it for another.
  // Verified rules are set per category (student, senior or PWD separately),
  // so one of them cannot stand for the grouped discount choice.
  const quotedFor = fare.passenger_category ?? DEFAULT_PASSENGER
  if (passenger !== 'regular' || quotedFor !== 'regular' || !isCentavos(fare.amount_centavos)) return NO_FARE
  return {
    low: fare.amount_centavos,
    high: fare.amount_centavos,
    basis: 'verified',
    estimated: fare.status === 'approximate',
    vehicleSelectable: false,
  }
}

function usableEstimate(estimate: GuideFareEstimate | null | undefined): GuideFareEstimate | null {
  if (!estimate || estimate.status !== 'available' || !estimate.amounts_centavos) return null
  const amounts = estimate.amounts_centavos
  const complete = (['traditional', 'modern'] as const).every(
    (type) => isCentavos(amounts[type]?.regular) && isCentavos(amounts[type]?.discounted),
  )
  return complete ? estimate : null
}

export function defaultVehicleChoice(segment: RideSegment): VehicleChoice {
  return usableEstimate(segment.guide_fare_estimate)?.known_vehicle_type ?? 'unsure'
}

export function rideFare(segment: RideSegment, vehicle: VehicleChoice, passenger: PassengerType): RideFare {
  // Verified fares keep priority and are never replaced by a guide estimate.
  if (hasVerifiedQuote(segment)) return verifiedFare(segment, passenger)

  const estimate = usableEstimate(segment.guide_fare_estimate)
  if (!estimate?.amounts_centavos) return NO_FARE
  const column = fareColumn(passenger)
  const traditional = estimate.amounts_centavos.traditional[column]
  const modern = estimate.amounts_centavos.modern[column]
  const [low, high] =
    vehicle === 'traditional'
      ? [traditional, traditional]
      : vehicle === 'modern'
        ? [modern, modern]
        : [Math.min(traditional, modern), Math.max(traditional, modern)]
  return { low, high, basis: 'estimate', estimated: true, vehicleSelectable: true }
}

export function defaultVehicleChoices(option: JourneyOption): VehicleChoice[] {
  return rides(option).map(defaultVehicleChoice)
}

// Each ride is priced on its own distance and choices, then the rides' lows
// and highs are added separately to give the trip range.
export function tripFare(option: JourneyOption, vehicles: VehicleChoice[], passenger: PassengerType): TripFare {
  const legs = rides(option)
  const rideFares = legs.map((segment, index) =>
    rideFare(segment, vehicles[index] ?? defaultVehicleChoice(segment), passenger),
  )
  const complete = rideFares.length > 0 && rideFares.every((f) => f.low !== null && f.high !== null)
  const total = complete
    ? {
        low: rideFares.reduce((sum, f) => sum + (f.low as number), 0),
        high: rideFares.reduce((sum, f) => sum + (f.high as number), 0),
      }
    : null
  return { rides: rideFares, total, estimated: rideFares.some((f) => f.estimated) }
}

export const ASK_DRIVER_FOR_RIDE = "Ask the driver for this ride's fare."

function toDisplay(low: number | null, high: number | null, estimated: boolean): FareDisplay {
  if (low === null || high === null) {
    return { text: 'Ask the driver', amount: null, estimated: false, reason: null }
  }
  const amount = formatFareRange(low, high)
  return { text: estimated ? `${amount} Estimated` : amount, amount, estimated, reason: null }
}

export function rideFareDisplay(fare: RideFare): FareDisplay {
  return toDisplay(fare.low, fare.high, fare.estimated)
}

export function tripFareDisplay(fare: TripFare): FareDisplay {
  return toDisplay(fare.total?.low ?? null, fare.total?.high ?? null, fare.estimated)
}
