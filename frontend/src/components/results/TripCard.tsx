import { ArrowRight, BusFront, ChevronDown, Clock, Footprints, MapPinned, ShieldCheck } from 'lucide-react'
import { memo, useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import type { JourneyOption } from '../../api'
import { totalFareDisplay } from '../../fareDisplay'
import { formatDistance, formatDuration } from '../../format'
import {
  buildTimeline,
  needsLocalCheck,
  rideColor,
  rides,
  straightLineWalkingMeters,
  transferLabel,
  tripName,
  type TripEndpoints,
} from '../../tripTimeline'
import InfoTip from '../ui/InfoTip'
import FareText from './FareText'
import TripTimeline from './TripTimeline'

const SORT_LABELS: Record<string, string> = {
  fewest_transfers: 'Fewest transfers',
  cheapest: 'Cheapest',
  fastest: 'Fastest',
  least_walking: 'Least walking',
}

interface Props {
  option: JourneyOption
  index: number
  endpoints: TripEndpoints
  expanded: boolean
  onMap: boolean
  onToggle: (id: string) => void
}

function RoutePlates({ option }: { option: JourneyOption }) {
  return (
    <span className="flex flex-wrap items-center gap-1">
      {rides(option).map((ride, k) => (
        <span key={k} className="flex items-center gap-1">
          {k > 0 && <ArrowRight size={13} className="text-ink-soft" aria-label="then" />}
          <span className="route-plate" style={{ backgroundColor: rideColor(k) }}>
            <BusFront size={13} aria-hidden="true" />
            {ride.route_code}
          </span>
        </span>
      ))}
    </span>
  )
}

function Stat({ label, children, info }: { label: string; children: ReactNode; info?: string }) {
  return (
    <div className="min-w-0 rounded-[4px] border border-line bg-brand-50/60 px-2.5 py-2">
      <p className="flex items-center gap-1 text-[11px] font-semibold tracking-wide text-ink-soft uppercase">
        {label}
        {info && <InfoTip label={`About ${label.toLowerCase()}`}>{info}</InfoTip>}
      </p>
      <div className="mt-0.5 text-sm font-semibold whitespace-nowrap text-ink">{children}</div>
    </div>
  )
}

function DataNote({ option }: { option: JourneyOption }) {
  const codes = rides(option).map((r) => r.route_code)
  const sources = option.evidence.references.filter((r) => r.title)
  const verified = !needsLocalCheck(option)
  return (
    <div className="mt-1 flex items-start gap-2 rounded-[4px] border border-line bg-surface/60 px-2.5 py-2 text-xs text-ink-muted">
      <ShieldCheck size={15} className="mt-px shrink-0 text-brand-500" aria-hidden="true" />
      <p className="min-w-0 flex-1">
        {verified
          ? 'This route has been checked on the ground.'
          : `Check locally that ${codes.join(' and ')} still ${codes.length > 1 ? 'run' : 'runs'} this way.`}
      </p>
      {/* Technical provenance stays available for those who want it. */}
      <InfoTip label="About this route data">
        <span className="block">
          Status: {verified ? 'field-verified' : 'documented (published or historic) data, not field-verified'}.
        </span>
        {option.warnings.map((w) => (
          <span key={w} className="mt-1 block">
            {w}
          </span>
        ))}
        {sources.length > 0 && (
          <span className="mt-1 block text-ink-soft">
            Source: {sources.map((r) => (r.publisher ? `${r.title} (${r.publisher})` : r.title)).join('; ')}
          </span>
        )}
      </InfoTip>
    </div>
  )
}

function TripCard({ option, index, endpoints, expanded, onMap, onToggle }: Props) {
  const name = tripName(option)
  const fare = totalFareDisplay(option.fare)
  const riding = option.time.riding_seconds
  const walking = straightLineWalkingMeters(option)
  const panelId = `trip-${option.id}`
  const [mounted, setMounted] = useState(expanded)
  if (expanded && !mounted) setMounted(true)
  const card = useRef<HTMLLIElement>(null)

  // Bring a newly opened trip into view once the expand animation has started.
  useEffect(() => {
    if (!expanded) return
    const timer = window.setTimeout(() => {
      const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches
      card.current?.scrollIntoView({ block: 'nearest', behavior: smooth ? 'smooth' : 'auto' })
    }, 300)
    return () => window.clearTimeout(timer)
  }, [expanded])

  return (
    <li
      ref={card}
      className={`fade-up group relative rounded-[4px] border bg-white transition-[border-color,box-shadow,transform] duration-200 ${
        expanded
          ? 'border-brand-500 shadow-[0_4px_14px_rgb(6_47_87/0.12)]'
          : onMap
            ? 'border-brand-400 hover:shadow-[0_3px_10px_rgb(6_47_87/0.10)]'
            : 'border-line hover:-translate-y-px hover:border-brand-300 hover:shadow-[0_3px_10px_rgb(6_47_87/0.10)]'
      }`}
      style={{ '--i': Math.min(index, 8) } as CSSProperties}
    >
      {onMap && <span className="absolute inset-y-0 left-0 w-[3px] rounded-l-[3px] bg-brand-500" aria-hidden="true" />}
      <h3>
        <button
          type="button"
          onClick={() => onToggle(option.id)}
          aria-expanded={expanded}
          aria-controls={panelId}
          className="focus-ring flex w-full items-start gap-3 rounded-[4px] p-3 pl-3.5 text-left"
        >
          <span className="min-w-0 flex-1">
            <span className="flex flex-wrap items-center gap-1.5">
              <RoutePlates option={option} />
              {option.labels.map((l) => (
                <span key={l} className="badge badge-blue">
                  {SORT_LABELS[l] ?? l}
                </span>
              ))}
            </span>
            <span className="mt-2 flex flex-wrap items-center gap-x-1.5 text-[15px] leading-snug font-semibold text-ink">
              <span className="break-words">{name.from}</span>
              <ArrowRight size={15} className="shrink-0 text-brand-500" aria-label="to" />
              <span className="break-words">{name.to}</span>
            </span>
            <span className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-muted">
              <span className={`badge ${option.transfers === 0 ? 'badge-blue' : ''}`}>{transferLabel(option.transfers)}</span>
              <span>{fare.amount ? (fare.estimated ? `${fare.amount} Estimated` : fare.amount) : 'Ask driver for fare'}</span>
              {riding !== null && (
                <span className="inline-flex items-center gap-1">
                  <Clock size={13} aria-hidden="true" />
                  {formatDuration(riding)} ride
                </span>
              )}
              {onMap && (
                <span className="inline-flex items-center gap-1 font-semibold text-brand-600">
                  <MapPinned size={13} aria-hidden="true" />
                  On map
                </span>
              )}
            </span>
          </span>
          <span
            className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-[4px] border border-line text-brand-600 transition-colors group-hover:border-brand-300 group-hover:bg-brand-50"
            aria-hidden="true"
          >
            <ChevronDown size={16} className="chevron" />
          </span>
        </button>
      </h3>

      <div className="accordion" data-open={expanded}>
        <div id={panelId} inert={!expanded}>
          <div className="border-t border-line px-3 pt-3 pb-3">
            <div className="mb-4 grid grid-cols-[1.2fr_1fr_1fr] gap-1.5">
              <Stat label="Fare">
                <FareText fare={fare} short />
              </Stat>
              <Stat label="Riding" info={riding !== null ? 'From older published schedules; traffic can change it.' : undefined}>
                {riding !== null ? formatDuration(riding) : '—'}
              </Stat>
              <Stat
                label="Walking"
                info={walking !== null ? 'At least this far: measured in straight lines, so the street route is longer.' : undefined}
              >
                <span className="inline-flex items-center gap-1">
                  <Footprints size={13} className="text-ink-soft" aria-hidden="true" />
                  {walking !== null ? formatDistance(walking) : '—'}
                </span>
              </Stat>
            </div>
            {/* Built on first open (cheap for long lists), then kept so collapsing animates smoothly. */}
            {mounted && <TripTimeline steps={buildTimeline(option, endpoints)} />}
            <DataNote option={option} />
          </div>
        </div>
      </div>
    </li>
  )
}

export default memo(TripCard)
