import { ArrowLeft, ArrowRight, Banknote, Clock, Footprints, PanelLeftClose, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'
import type { JourneyOption } from '../../api'
import { totalFareDisplay } from '../../fareDisplay'
import { formatDistance, formatDuration } from '../../format'
import { buildTimeline, needsLocalCheck, straightLineWalkingMeters, transferLabel, tripName, type TripEndpoints } from '../../tripTimeline'
import JourneyStrip from './JourneyStrip'
import TripFare from './TripFare'
import TripTimeline from './TripTimeline'

interface HeaderProps {
  // Desktop hides the panel; phones go back to the trip list.
  onClose: () => void
  closeMode: 'hide' | 'back'
}

function Fact({ icon, label, children }: { icon: ReactNode; label: string; children: ReactNode }) {
  return (
    <div className="min-w-0 rounded-[4px] border border-line bg-white px-2.5 py-2">
      <p className="flex items-center gap-1 text-[11px] font-semibold tracking-wide text-ink-soft uppercase">
        {icon}
        {label}
      </p>
      <div className="mt-0.5 truncate text-sm font-semibold text-ink">{children}</div>
    </div>
  )
}

export function TripDetailsHeader({ onClose, closeMode }: HeaderProps) {
  return (
      <header className="titlebar flex h-14 shrink-0 items-center gap-2 px-3">
        {closeMode === 'back' && (
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 items-center gap-1 rounded-[3px] border border-brand-900/60 bg-white/10 px-2 text-sm font-semibold text-white hover:bg-white/25 focus-visible:outline-2 focus-visible:outline-white"
          >
            <ArrowLeft size={16} aria-hidden="true" />
            All trips
          </button>
        )}
        <h2 className="min-w-0 flex-1 truncate font-pixel text-base font-bold tracking-wide">Trip details</h2>
        {closeMode === 'hide' && (
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-[3px] border border-brand-900/60 bg-white/10 text-white transition-colors hover:bg-white/25 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            aria-label="Hide trip details"
            title="Hide trip details"
          >
            <PanelLeftClose size={17} aria-hidden="true" />
          </button>
        )}
      </header>
  )
}

// Summary and timeline for one trip. Callers key it by trip ID so the entry
// animation replays and no stale steps remain when another trip is picked.
export default function TripDetails({ option, endpoints }: { option: JourneyOption; endpoints: TripEndpoints }) {
  const name = tripName(option)
  const riding = option.time.riding_seconds
  const walking = straightLineWalkingMeters(option)

  return (
      <div>
        <section className="fade-up space-y-3 border-b border-line bg-white p-3">
          <p className="flex flex-wrap items-center gap-x-1.5 text-lg leading-snug font-bold text-ink">
            <span className="break-words">{name.from}</span>
            <ArrowRight size={17} className="shrink-0 text-brand-500" aria-label="to" />
            <span className="break-words">{name.to}</span>
          </p>
          <JourneyStrip option={option} />
          <div className="grid grid-cols-[1fr_1fr_1.25fr] gap-1.5">
            <Fact icon={<Clock size={12} aria-hidden="true" />} label="Ride">
              {riding !== null ? formatDuration(riding) : '—'}
            </Fact>
            <Fact icon={<Footprints size={12} aria-hidden="true" />} label="Walk">
              {walking !== null ? `${formatDistance(walking)}+` : '—'}
            </Fact>
            <Fact icon={<Banknote size={12} aria-hidden="true" />} label="Fare">
              <TripFare fare={totalFareDisplay(option.fare)} short />
            </Fact>
          </div>
          <span className={`badge ${option.transfers === 0 ? 'badge-blue' : ''}`}>{transferLabel(option.transfers)}</span>
        </section>

        <section className="p-3 pl-4" aria-label="Directions">
          <TripTimeline steps={buildTimeline(option, endpoints)} />
          {needsLocalCheck(option) && (
            <p className="mt-4 flex items-start gap-2 rounded-[4px] border border-caution/25 bg-caution-50 px-3 py-2 text-xs text-caution">
              <TriangleAlert size={15} className="mt-px shrink-0" aria-hidden="true" />
              Routes can change. Check the signboard or ask the driver before you ride.
            </p>
          )}
        </section>
      </div>
  )
}
