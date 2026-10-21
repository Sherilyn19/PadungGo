import { Footprints } from 'lucide-react'
import type { JourneyOption } from '../../api'
import { rideColor, rides } from '../../tripTimeline'

// At-a-glance bar of the trip: walks in grey, each ride in its own colour,
// sized by ride time (or distance when time is unknown).
export default function JourneyStrip({ option }: { option: JourneyOption }) {
  const legs = rides(option)
  const walk = (key: string) => (
    <span key={key} className="flex w-6 shrink-0 items-center justify-center text-ink-soft" aria-hidden="true">
      <Footprints size={13} />
    </span>
  )
  return (
    <div className="flex h-7 items-center gap-0.5" aria-hidden="true">
      {walk('start')}
      {legs.map((ride, i) => (
        <span key={i} className="contents">
          {i > 0 && <span className="h-2 w-2 shrink-0 rounded-full border-2 border-ink-soft bg-white" />}
          <span
            className="flex h-6 min-w-12 items-center justify-center rounded-[4px] text-[11px] font-bold text-white"
            style={{ flexGrow: Math.max(1, ride.duration_seconds ?? ride.distance_m ?? 1), backgroundColor: rideColor(i) }}
          >
            {ride.route_code}
          </span>
        </span>
      ))}
      {walk('end')}
    </div>
  )
}
