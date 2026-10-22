import { Banknote } from 'lucide-react'
import { ASK_DRIVER_FOR_RIDE, rideFareDisplay, type RideFare, type VehicleChoice } from '../../fareEstimates'
import TripFare from '../trips/TripFare'
import VehicleTypeSelector from './VehicleTypeSelector'

interface Props {
  routeCode: string
  color: string
  fare: RideFare
  vehicle: VehicleChoice
  onVehicleChange: (vehicle: VehicleChoice) => void
}

// Bottom of a ride block: the jeepney type picker (only when it changes the
// estimate) and this ride's fare.
export default function RideFareFooter({ routeCode, color, fare, vehicle, onVehicleChange }: Props) {
  const display = rideFareDisplay(fare)
  return (
    <div className="space-y-2 rounded-[6px] border border-white/70 bg-white/80 p-2">
      {fare.vehicleSelectable && <VehicleTypeSelector routeCode={routeCode} value={vehicle} onChange={onVehicleChange} accent={color} />}
      <p className="flex items-center gap-1.5 text-sm" aria-live="polite">
        <Banknote size={15} style={{ color }} aria-hidden="true" />
        <span className="text-xs font-semibold text-ink-muted">Fare</span>
        {display.amount ? <TripFare fare={display} /> : <span className="text-xs text-ink-muted">{ASK_DRIVER_FOR_RIDE}</span>}
      </p>
    </div>
  )
}
