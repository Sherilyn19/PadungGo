import type { CSSProperties } from 'react'
import { BusFront, ChevronRight, Hourglass } from 'lucide-react'
import type { RideSegment } from '../../api'
import { isScarceRide, rideColor } from '../../tripTimeline'

// Route code styled like a jeepney signboard plate, in its ride's colour.
export default function RidePlate({ code, rideIndex, size = 'md' }: { code: string; rideIndex: number; size?: 'md' | 'lg' }) {
  return (
    <span
      className={`route-plate ${size === 'lg' ? 'h-7 px-2 text-[15px]' : ''}`}
      style={{ backgroundColor: rideColor(rideIndex), '--route-glow': rideColor(rideIndex) } as CSSProperties}
    >
      <BusFront size={size === 'lg' ? 15 : 13} aria-hidden="true" />
      {code}
    </span>
  )
}

// Shown next to a ride whose route commuters report has few trips. No waiting
// time is known, so the wording stays general.
export function ScarceBadge() {
  return (
    <span className="badge badge-scarce" title="Few jeepneys">
      <Hourglass size={12} aria-hidden="true" />
      Scarce
    </span>
  )
}

export function RidePlates({ rides }: { rides: RideSegment[] }) {
  return (
    <span className="flex flex-wrap items-center gap-1">
      {rides.map((ride, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <ChevronRight size={13} className="text-ink-soft" aria-label="then" />}
          <RidePlate code={ride.route_code} rideIndex={i} />
          {isScarceRide(ride) && <ScarceBadge />}
        </span>
      ))}
    </span>
  )
}
