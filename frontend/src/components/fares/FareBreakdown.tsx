import type { RideSegment } from '../../api'
import { ASK_DRIVER_FOR_RIDE, rideFareDisplay, tripFareDisplay, type TripFare as TripFareTotals } from '../../fareEstimates'
import { rideColor } from '../../tripTimeline'
import RidePlate from '../trips/RidePlate'
import TripFare from '../trips/TripFare'

// Each ride's fare and the trip total, without formulas.
export default function FareBreakdown({ rides, fare }: { rides: RideSegment[]; fare: TripFareTotals }) {
  if (rides.length === 0) return null
  return (
    <section aria-label="Fare breakdown" className="rounded-[6px] border border-cream-line bg-white">
      <h3 className="section-label border-b border-cream-line px-3 py-2">Fare breakdown</h3>
      <ul className="divide-y divide-cream-line">
        {rides.map((ride, index) => {
          const display = rideFareDisplay(fare.rides[index])
          return (
            <li key={index} className="flex items-center gap-2 px-3 py-2 text-sm">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: rideColor(index) }} aria-hidden="true" />
              <span className="font-semibold text-ink-muted">Ride {index + 1}</span>
              <RidePlate code={ride.route_code} rideIndex={index} />
              <span className="ml-auto text-right">
                {display.amount ? <TripFare fare={display} /> : <span className="text-xs text-ink-muted">{ASK_DRIVER_FOR_RIDE}</span>}
              </span>
            </li>
          )
        })}
      </ul>
      {rides.length > 1 && (
        <p className="flex items-center justify-between gap-2 border-t border-cream-line bg-cream px-3 py-2 text-sm font-semibold">
          <span>Total</span>
          <TripFare fare={tripFareDisplay(fare)} />
        </p>
      )}
    </section>
  )
}
