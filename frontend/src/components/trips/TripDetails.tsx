import { ArrowLeft, ArrowRight, Clock, Footprints, PanelLeftClose, Signpost } from 'lucide-react'
import type { ReactNode } from 'react'
import type { JourneyOption, TripSearch } from '../../api'
import { tripFare, type PassengerType, type VehicleChoice } from '../../fareEstimates'
import { formatCalendarDate, formatDuration, formatMinimumDistance } from '../../format'
import { buildTimeline, needsLocalCheck, rideColor, rides, straightLineWalkingMeters, transferLabel, tripName, type TripEndpoints } from '../../tripTimeline'
import FareBreakdown from '../fares/FareBreakdown'
import PassengerSelector from '../fares/PassengerSelector'
import RideFareFooter from '../fares/RideFareFooter'
import TripFareSummary from '../fares/TripFareSummary'
import JourneyStrip from './JourneyStrip'
import TripExplanation from './TripExplanation'
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
      <header className="titlebar titlebar-light flex h-14 shrink-0 items-center gap-2 px-3">
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

interface Props {
  option: JourneyOption
  endpoints: TripEndpoints
  // The search behind this trip, used only by "Explain this trip".
  search: TripSearch | null
  // Date of the last route-data change, from the server ("YYYY-MM-DD").
  dataUpdatedOn?: string | null
  passenger: PassengerType
  vehicles: VehicleChoice[]
  onPassengerChange: (passenger: PassengerType) => void
  onVehicleChange: (rideIndex: number, vehicle: VehicleChoice) => void
}

// Summary, fare choices and timeline for one trip. Callers key it by trip ID
// so the entry animation replays and no stale steps remain when another trip
// is picked. Fare choices live in the parent, so changing them updates the
// amounts in place without reloading or resetting the panel.
export default function TripDetails({ option, endpoints, search, dataUpdatedOn, passenger, vehicles, onPassengerChange, onVehicleChange }: Props) {
  const name = tripName(option)
  const riding = option.time.riding_seconds
  const walking = straightLineWalkingMeters(option)
  const legs = rides(option)
  const fare = tripFare(option, vehicles, passenger)
  const updated = formatCalendarDate(dataUpdatedOn)

  return (
      <div>
        <section className="fade-up space-y-3 border-b border-cream-line bg-white p-3">
          <p className="flex flex-wrap items-center gap-x-1.5 text-lg leading-snug font-bold text-ink">
            <span className="break-words">{name.from}</span>
            <ArrowRight size={17} className="shrink-0 text-brand-500" aria-label="to" />
            <span className="break-words">{name.to}</span>
          </p>
          <JourneyStrip option={option} />
          <TripFareSummary fare={fare} transfers={transferLabel(option.transfers)} direct={option.transfers === 0} />
          <div className="grid grid-cols-2 gap-1.5">
            <Fact icon={<Clock size={12} aria-hidden="true" />} label="Ride">
              {riding !== null ? formatDuration(riding) : '—'}
            </Fact>
            <Fact icon={<Footprints size={12} aria-hidden="true" />} label="Walk">
              {walking !== null ? formatMinimumDistance(walking) : '—'}
            </Fact>
          </div>
          <PassengerSelector value={passenger} onChange={onPassengerChange} />
        </section>

        <TripExplanation option={option} search={search} />

        <section className="space-y-4 p-3 pl-4" aria-label="Directions">
          <TripTimeline
            steps={buildTimeline(option, endpoints)}
            rideFooter={(rideIndex) => (
              <RideFareFooter
                routeCode={legs[rideIndex].route_code}
                color={rideColor(rideIndex)}
                fare={fare.rides[rideIndex]}
                vehicle={vehicles[rideIndex] ?? 'unsure'}
                onVehicleChange={(vehicle) => onVehicleChange(rideIndex, vehicle)}
              />
            )}
          />
          <FareBreakdown rides={legs} fare={fare} />
          {needsLocalCheck(option) && (
            <div className="flex items-start gap-2 rounded-[6px] border border-moss-200 bg-moss-50 px-3 py-2 text-moss-800">
              <Signpost size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
              <div className="min-w-0">
                {/* Bisaya: "Keep going! Read the signboard or ask the driver before you ride." */}
                <p className="text-sm font-semibold">Padayon lang! Basaha ang karatula o pangutan-a ang drayber sa dili pa ka mosakay.</p>
                {updated && <p className="mt-0.5 text-xs text-ink-muted">Route info updated {updated}</p>}
              </div>
            </div>
          )}
        </section>
      </div>
  )
}
