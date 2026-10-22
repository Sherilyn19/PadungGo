import { useCallback, useReducer } from 'react'
import type { JourneyOption } from '../api'
import {
  DEFAULT_PASSENGER,
  defaultVehicleChoices,
  tripFare,
  type PassengerType,
  type TripFare,
  type VehicleChoice,
} from '../fareEstimates'

// The commuter's fare choices. They only change what this screen shows and
// are never sent back to change route records.
export interface FareChoices {
  passenger: PassengerType
  // Jeepney type per ride, keyed by trip ID. Missing trips use defaults.
  vehicles: Record<string, VehicleChoice[]>
}

export type FareChoicesAction =
  | { type: 'passenger'; passenger: PassengerType }
  | { type: 'vehicle'; option: JourneyOption; rideIndex: number; vehicle: VehicleChoice }
  // New search results: old trip IDs no longer apply, the passenger type does.
  | { type: 'reset-vehicles' }

export const INITIAL_FARE_CHOICES: FareChoices = { passenger: DEFAULT_PASSENGER, vehicles: {} }

export function vehicleChoicesFor(choices: FareChoices, option: JourneyOption): VehicleChoice[] {
  return choices.vehicles[option.id] ?? defaultVehicleChoices(option)
}

export function fareChoicesReducer(state: FareChoices, action: FareChoicesAction): FareChoices {
  switch (action.type) {
    case 'passenger':
      return state.passenger === action.passenger ? state : { ...state, passenger: action.passenger }
    case 'vehicle': {
      const current = vehicleChoicesFor(state, action.option)
      if (action.rideIndex < 0 || action.rideIndex >= current.length) return state
      const next = current.slice()
      next[action.rideIndex] = action.vehicle
      return { ...state, vehicles: { ...state.vehicles, [action.option.id]: next } }
    }
    case 'reset-vehicles':
      return Object.keys(state.vehicles).length ? { ...state, vehicles: {} } : state
  }
}

export function tripFareFor(choices: FareChoices, option: JourneyOption): TripFare {
  return tripFare(option, vehicleChoicesFor(choices, option), choices.passenger)
}

export function useFareChoices() {
  const [choices, dispatch] = useReducer(fareChoicesReducer, INITIAL_FARE_CHOICES)
  const setPassenger = useCallback((passenger: PassengerType) => dispatch({ type: 'passenger', passenger }), [])
  const setVehicle = useCallback(
    (option: JourneyOption, rideIndex: number, vehicle: VehicleChoice) =>
      dispatch({ type: 'vehicle', option, rideIndex, vehicle }),
    [],
  )
  const resetVehicles = useCallback(() => dispatch({ type: 'reset-vehicles' }), [])
  return { choices, setPassenger, setVehicle, resetVehicles }
}
