import type { FareDisplay } from '../../fareDisplay'

// "₱14.00", "₱14.00 Estimated" or "Ask the driver" — never a guessed amount.
export default function TripFare({ fare, short = false }: { fare: FareDisplay; short?: boolean }) {
  if (!fare.amount) return <span>{short ? 'Ask driver' : 'Ask the driver'}</span>
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="font-semibold text-ink">{fare.amount}</span>
      {fare.estimated && <span className="badge badge-blue h-5 px-1 text-[10px]">Estimated</span>}
    </span>
  )
}
