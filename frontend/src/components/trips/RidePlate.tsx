import { BusFront, ChevronRight } from 'lucide-react'
import { rideColor } from '../../tripTimeline'

// Route code styled like a jeepney signboard plate, in its ride's colour.
export default function RidePlate({ code, rideIndex, size = 'md' }: { code: string; rideIndex: number; size?: 'md' | 'lg' }) {
  return (
    <span
      className={`route-plate ${size === 'lg' ? 'h-7 px-2 text-[15px]' : ''}`}
      style={{ backgroundColor: rideColor(rideIndex) }}
    >
      <BusFront size={size === 'lg' ? 15 : 13} aria-hidden="true" />
      {code}
    </span>
  )
}

export function RidePlates({ codes }: { codes: string[] }) {
  return (
    <span className="flex flex-wrap items-center gap-1">
      {codes.map((code, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <ChevronRight size={13} className="text-ink-soft" aria-label="then" />}
          <RidePlate code={code} rideIndex={i} />
        </span>
      ))}
    </span>
  )
}
