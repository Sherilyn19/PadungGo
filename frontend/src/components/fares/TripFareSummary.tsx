import { Banknote } from 'lucide-react'
import { tripFareDisplay, type TripFare } from '../../fareEstimates'

interface Props {
  fare: TripFare
  transfers: string
  direct: boolean
}

// The trip's headline fare with its transfer count. A total only appears
// when every ride has a fare, so it is never a partial sum.
export default function TripFareSummary({ fare, transfers, direct }: Props) {
  const display = tripFareDisplay(fare)
  return (
    <div className="bg-dots flex items-center gap-3 rounded-[6px] border border-cream-line px-3 py-2.5">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-moss-600 text-white" aria-hidden="true">
        <Banknote size={18} />
      </span>
      <div className="min-w-0 flex-1" aria-live="polite">
        <p className="text-xs font-semibold text-ink-muted">{display.estimated ? 'Estimated total' : 'Total fare'}</p>
        {display.amount ? (
          // Sans digits: the pixel face makes 5 and S look alike in prices.
          <p className="text-xl leading-tight font-bold text-charcoal tabular-nums">{display.amount}</p>
        ) : (
          <p className="text-sm font-semibold text-ink">Ask the driver for the fare</p>
        )}
      </div>
      <span className={`badge ${direct ? 'badge-blue' : ''}`}>{transfers}</span>
    </div>
  )
}
