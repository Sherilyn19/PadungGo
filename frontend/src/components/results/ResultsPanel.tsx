import { CircleAlert, MapPin, RotateCcw, Route, Search, TriangleAlert, Undo2 } from 'lucide-react'
import { useState } from 'react'
import type { PlanResponse } from '../../api'
import { explainRanking, explainReason } from '../../format'
import type { TripEndpoints } from '../../tripTimeline'
import InfoTip from '../ui/InfoTip'
import TripCard from './TripCard'

// Cards shown before "Show more". All results are already loaded; this only
// keeps the first view short and fast to render.
const PAGE_SIZE = 8

interface Props {
  plan: PlanResponse | null
  loading: boolean
  slow: boolean
  error: string | null
  onRetry: (() => void) | null
  isReturn: boolean
  onSwitchDirection: (() => void) | null
  selectedId: string | null
  expandedId: string | null
  onToggle: (id: string) => void
  endpoints: TripEndpoints
  maxTransfers: 0 | 1
  onAllowTransfer: () => void
}

function Landing() {
  const steps = [
    { icon: MapPin, title: 'Choose where you start', text: 'Search a street or landmark, use your location, or tap the map.' },
    { icon: Search, title: 'Choose where you’re going', text: 'Then press Find trips.' },
    { icon: Route, title: 'Pick a trip', text: 'Open a trip to see each jeepney, where to board and where to get off.' },
  ]
  return (
    <section className="card fade-up p-3" aria-labelledby="how-it-works">
      <h2 id="how-it-works" className="section-label mb-2.5">
        How it works
      </h2>
      <ol className="space-y-3">
        {steps.map(({ icon: Icon, title, text }, i) => (
          <li key={title} className="fade-up flex gap-3" style={{ ['--i' as string]: i + 1 }}>
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[4px] border border-brand-800 bg-brand-500 text-white">
              <Icon size={16} aria-hidden="true" />
            </span>
            <span>
              <span className="block text-sm font-semibold text-ink">{title}</span>
              <span className="block text-xs text-ink-muted">{text}</span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}

function Loading({ slow }: { slow: boolean }) {
  return (
    <div className="space-y-3" aria-hidden="true">
      <div className="card p-3">
        <p className="section-label mb-2 text-brand-700">Finding trips…</p>
        <div className="progress-retro" />
      </div>
      {slow && (
        <p className="card fade-up p-3 text-sm text-ink-muted">
          The server is waking up (free hosting sleeps when idle). This can take up to a minute.
        </p>
      )}
      {[0, 1, 2].map((k) => (
        <div key={k} className="card space-y-2 p-3">
          <div className="skeleton h-5 w-24 rounded-[3px]" />
          <div className="skeleton h-4 w-3/4 rounded-[3px]" />
          <div className="skeleton h-3 w-1/2 rounded-[3px]" />
        </div>
      ))}
    </div>
  )
}

function Empty({ plan, maxTransfers, onAllowTransfer, onSwitchDirection }: Pick<Props, 'maxTransfers' | 'onAllowTransfer' | 'onSwitchDirection'> & { plan: PlanResponse }) {
  return (
    <div className="card fade-up p-4 text-center" role="status">
      <span className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-brand-500">
        <Route size={20} aria-hidden="true" />
      </span>
      <p className="mt-2 font-semibold text-ink">No trip found</p>
      <p className="mt-1 text-sm text-ink-muted">{explainReason(plan.reason)}</p>
      <div className="mt-3 flex flex-wrap justify-center gap-2">
        {maxTransfers === 0 && plan.reason === 'no_journey_within_mvp_limits' && (
          <button type="button" className="btn btn-primary" onClick={onAllowTransfer}>
            Allow 1 transfer
          </button>
        )}
        {onSwitchDirection && plan.reason === 'no_journey_within_mvp_limits' && (
          <button type="button" className="btn" onClick={onSwitchDirection}>
            <Undo2 size={15} aria-hidden="true" />
            Check the trip back
          </button>
        )}
      </div>
      <p className="mt-3 text-xs text-ink-soft">
        A jeepney may still serve this trip; our route data just doesn’t include one yet.
      </p>
    </div>
  )
}

function DirectionTabs({ isReturn, onSwitch, count }: { isReturn: boolean; onSwitch: (() => void) | null; count: number }) {
  const tab = (active: boolean) =>
    `focus-ring -mb-px h-8 rounded-t-[4px] border px-3 text-xs font-semibold transition-colors ${
      active
        ? 'border-line border-b-white bg-white text-ink'
        : 'border-transparent bg-surface text-ink-soft hover:text-brand-700'
    }`
  return (
    <div className="flex items-end justify-between border-b border-line">
      <div className="flex gap-1">
        <button type="button" className={tab(!isReturn)} aria-pressed={!isReturn} onClick={isReturn ? (onSwitch ?? undefined) : undefined}>
          Going
        </button>
        <button type="button" className={tab(isReturn)} aria-pressed={isReturn} onClick={!isReturn ? (onSwitch ?? undefined) : undefined}>
          Return
        </button>
      </div>
      <p className="pb-1.5 text-xs text-ink-soft" aria-live="polite">
        {count} {count === 1 ? 'trip' : 'trips'} found
      </p>
    </div>
  )
}

function TripList({ plan, ...props }: Props & { plan: PlanResponse }) {
  const [visible, setVisible] = useState(PAGE_SIZE)
  const options = plan.journey_options
  const shown = options.slice(0, visible)
  const remaining = options.length - shown.length
  const anyDocumented = options.some((o) => o.evidence.verification_status !== 'verified')
  const ranking = explainRanking(plan.ranking)

  return (
    <div className="space-y-3">
      {anyDocumented && (
        <div className="flex items-start gap-2 rounded-[4px] border border-brand-200 bg-brand-50 px-3 py-2 text-xs text-brand-900">
          <TriangleAlert size={15} className="mt-px shrink-0 text-brand-600" aria-hidden="true" />
          <p className="min-w-0 flex-1">Routes come from older published data. Check locally that your jeepney still runs.</p>
          <InfoTip label="About the route data">
            {plan.warnings.map((w) => (
              <span key={w} className="block">
                {w}
              </span>
            ))}
            <span className="mt-1 block">Drivers, signboards and locals are the best guide to current service.</span>
          </InfoTip>
        </div>
      )}
      {ranking && <p className="text-xs text-ink-muted">{ranking}</p>}
      <ol className="space-y-2" aria-label="Trips">
        {shown.map((option, index) => (
          <TripCard
            key={option.id}
            option={option}
            index={index}
            endpoints={props.endpoints}
            expanded={option.id === props.expandedId}
            onMap={option.id === props.selectedId}
            onToggle={props.onToggle}
          />
        ))}
      </ol>
      {remaining > 0 && (
        <button type="button" className="btn w-full" onClick={() => setVisible((v) => v + PAGE_SIZE)}>
          Show {Math.min(remaining, PAGE_SIZE)} more {remaining === 1 ? 'trip' : 'trips'}
          <span className="font-normal text-ink-soft">({remaining} left)</span>
        </button>
      )}
    </div>
  )
}

export default function ResultsPanel(props: Props) {
  const { plan, loading, slow, error, onRetry } = props
  return (
    <>
      {/* Always mounted, so screen readers hear progress while the request runs. */}
      <div role="status" aria-live="polite" className="sr-only">
        {loading ? 'Finding trips…' : plan ? `${plan.journey_options.length} trips found` : ''}
      </div>
      <section className="space-y-3" aria-busy={loading} aria-label="Trip results">
        {loading && <Loading slow={slow} />}
        {!loading && error && (
          <div className="card fade-up flex items-start gap-2.5 border-alert/40 bg-alert-50 p-3 text-sm text-ink" role="alert">
            <CircleAlert size={18} className="mt-px shrink-0 text-alert" aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <p>{error}</p>
              {onRetry && (
                <button type="button" className="btn mt-2 min-h-8 px-2.5 text-xs" onClick={onRetry}>
                  <RotateCcw size={14} aria-hidden="true" />
                  Try again
                </button>
              )}
            </div>
          </div>
        )}
        {!loading && !error && !plan && <Landing />}
        {!loading && plan && (
          <>
            <DirectionTabs isReturn={props.isReturn} onSwitch={props.onSwitchDirection} count={plan.journey_options.length} />
            {plan.journey_options.length === 0 ? (
              <Empty plan={plan} maxTransfers={props.maxTransfers} onAllowTransfer={props.onAllowTransfer} onSwitchDirection={props.onSwitchDirection} />
            ) : (
              <TripList {...props} plan={plan} />
            )}
          </>
        )}
      </section>
    </>
  )
}
