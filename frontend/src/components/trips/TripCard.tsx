import { ArrowRight, ChevronRight, Clock } from 'lucide-react'
import { memo, type CSSProperties } from 'react'
import type { JourneyOption } from '../../api'
import type { FareDisplay } from '../../fareDisplay'
import { formatDuration } from '../../format'
import { rides, transferLabel, tripName } from '../../tripTimeline'
import { RidePlates } from './RidePlate'
import TripFare from './TripFare'

interface Props {
  option: JourneyOption
  index: number
  selected: boolean
  // Trip total for the commuter's current passenger and jeepney choices.
  fare: FareDisplay
  onSelect: (id: string) => void
}

// Compact, clickable trip summary. Details open in the trip details panel.
function TripCard({ option, index, selected, fare, onSelect }: Props) {
  const name = tripName(option)
  const riding = option.time.riding_seconds
  return (
    <li className="fade-up" style={{ '--i': Math.min(index, 8) } as CSSProperties}>
      <button
        type="button"
        onClick={() => onSelect(option.id)}
        aria-current={selected ? 'true' : undefined}
        aria-controls="trip-details"
        className={`focus-ring group relative flex w-full items-center gap-3 rounded-[4px] border bg-white p-3 text-left transition-[border-color,box-shadow,transform] duration-200 ${
          selected
            ? 'border-brand-500 shadow-[0_3px_10px_rgb(6_47_87/0.12)]'
            : 'border-line hover:-translate-y-px hover:border-brand-300 hover:shadow-[0_3px_10px_rgb(6_47_87/0.10)] active:translate-y-0'
        }`}
      >
        {selected && <span className="absolute inset-y-0 left-0 w-0.75 rounded-l-[3px] bg-brand-500" aria-hidden="true" />}
        <span className="min-w-0 flex-1">
                    <RidePlates rides={rides(option)} />
          <span className="mt-1.5 flex flex-wrap items-center gap-x-1.5 text-[15px] leading-snug font-semibold text-ink">
            <span className="wrap-break-word">{name.from}</span>
            <ArrowRight size={15} className="shrink-0 text-brand-500" aria-label="to" />
            <span className="wrap-break-word">{name.to}</span>
          </span>
          <span className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-muted">
            <span className={`badge ${option.transfers === 0 ? 'badge-blue' : ''}`}>{transferLabel(option.transfers)}</span>
            {riding !== null && (
              <span className="inline-flex items-center gap-1">
                <Clock size={13} aria-hidden="true" />
                {formatDuration(riding)} ride
              </span>
            )}
            <TripFare fare={fare} />
          </span>
        </span>
        <ChevronRight
          size={18}
          className={`shrink-0 transition-transform duration-200 group-hover:translate-x-0.5 ${selected ? 'text-brand-600' : 'text-ink-soft'}`}
          aria-hidden="true"
        />
      </button>
    </li>
  )
}

export default memo(TripCard)
