import type { JourneyOption, PlanResponse, RideSegment } from '../api'
import { explainReason, formatDistance, formatDuration } from '../format'
import { fareDisplay } from '../fareDisplay'
import { buildJourneySteps, straightLineWalkingMeters, type JourneyStep } from '../journeySteps'

interface Props {
  plan: PlanResponse
  selectedId: string | null
  onSelect: (id: string) => void
}

const LABELS: Record<string, string> = {
  fewest_transfers: 'Fewest transfers',
  cheapest: 'Cheapest',
  fastest: 'Fastest',
  least_walking: 'Least walking',
}

const STEP_ICONS: Record<JourneyStep['kind'], string> = { walk: '🚶', ride: '🚐', transfer: '🔁' }

function rides(o: JourneyOption): RideSegment[] {
  return o.segments.filter((s): s is RideSegment => s.mode === 'ride')
}

function Summary({ option }: { option: JourneyOption }) {
  const walking = straightLineWalkingMeters(option)
  const fare = fareDisplay({
    amount_centavos: option.fare.total_is_complete
      ? option.fare.total_centavos
      : null,
    status: option.fare.total_is_complete
      ? option.fare.status
      : 'unavailable',
    reason: option.fare.reason,
  })

  return (
    <>
      <span className="mt-2 grid grid-cols-3 gap-2 text-xs">
        <span className="min-w-0">
          <span className="block text-slate-500">Fare</span>
          <span className="block font-medium">{fare.text}</span>
        </span>
        <span className="min-w-0">
          <span className="block text-slate-500">Riding</span>
          <span className="block font-medium">
            {formatDuration(option.time.riding_seconds)}
            {option.time.riding_seconds !== null && (
              <span className="text-slate-500"> (schedule)</span>
            )}
          </span>
        </span>
        <span className="min-w-0">
          <span className="block text-slate-500">Walking</span>
          <span className="block font-medium">
            {walking === null ? (
              'Unknown'
            ) : (
              <>
                ≥ {formatDistance(walking)}
                <span className="text-slate-500"> (straight line)</span>
              </>
            )}
          </span>
        </span>
      </span>
      {fare.reason && (
        <span className="mt-2 block text-xs text-slate-600">
          {fare.reason}
        </span>
      )}
    </>
  )
}

function Steps({ option, id }: { option: JourneyOption; id: string }) {
  const steps = buildJourneySteps(option)
  return (
    <div id={id} className="journey-reveal border-t border-slate-200 px-3 pb-3 pt-3">
      <h3 className="sr-only">Step-by-step directions</h3>
      <ol className="space-y-3 text-sm">
        {steps.map((step, k) => (
          <li key={k} className="flex gap-3">
            <span
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white"
              style={{ backgroundColor: step.color ?? '#64748b' }}
            >
              {k + 1}
            </span>
            <div className="min-w-0">
              <p className="font-medium text-slate-900">
                <span aria-hidden="true">{STEP_ICONS[step.kind]} </span>
                {step.title}
              </p>
              {step.details.map((d) => (
                <p key={d} className="text-xs text-slate-700">{d}</p>
              ))}
              {step.caveats.map((c) => (
                <p key={c} className="text-xs text-slate-500">{c}</p>
              ))}
            </div>
          </li>
        ))}
        <li className="flex gap-3">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-red-600 text-xs text-white" aria-hidden="true">
            ✓
          </span>
          <p className="font-medium text-slate-900">Arrive at your destination</p>
        </li>
      </ol>
      <p className="mt-3 text-xs text-slate-500">Waiting time is unknown: there is no verified frequency data.</p>
      {option.warnings.length > 0 && (
        <ul className="mt-2 space-y-1">
          {option.warnings.map((w) => (
            <li key={w} className="text-xs text-amber-800">⚠ {w}</li>
          ))}
        </ul>
      )}
      {option.evidence.references.some((r) => r.title) && (
        <p className="mt-2 text-xs text-slate-500">
          Source:{' '}
          {option.evidence.references
            .filter((r) => r.title)
            .map((r) => (r.publisher ? `${r.title} (${r.publisher})` : r.title))
            .join('; ')}
        </p>
      )}
    </div>
  )
}

export default function Results({ plan, selectedId, onSelect }: Props) {
  if (plan.journey_options.length === 0) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="status">
        <p className="font-semibold">No journey found</p>
        <p className="mt-1">{explainReason(plan.reason)}</p>
        <p className="mt-1 text-xs">This does not prove that no jeepney serves this trip, only that the current data has none.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {plan.ranking.warning && <p className="text-xs text-slate-600">{plan.ranking.warning}</p>}
      <ol className="space-y-3" aria-label="Journey options">
        {plan.journey_options.map((o, i) => {
          const selected = o.id === selectedId
          const documented = o.evidence.verification_status !== 'verified'
          const panelId = `journey-steps-${o.id}`
          return (
            <li
              key={o.id}
              className={`rounded-lg border transition-colors motion-reduce:transition-none ${selected ? 'border-emerald-600 bg-emerald-50 ring-2 ring-emerald-200' : 'border-slate-200 bg-white hover:border-slate-300'}`}
            >
              <button
                type="button"
                onClick={() => onSelect(o.id)}
                aria-expanded={selected}
                aria-controls={panelId}
                className="w-full rounded-lg p-3 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
              >
                <span className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-slate-900">Option {i + 1}</span>
                  {rides(o).map((r, k) => (
                    <span key={k} className="rounded bg-slate-900 px-1.5 py-0.5 font-mono text-xs text-white">
                      {r.route_code}
                    </span>
                  ))}
                  <span className="text-xs text-slate-600">{o.transfers === 0 ? 'Direct' : '1 transfer'}</span>
                  {o.labels.map((l) => (
                    <span key={l} className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800">
                      {LABELS[l] ?? l}
                    </span>
                  ))}
                  {documented && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-900">
                      Historic data · not field-verified
                    </span>
                  )}
                  <span className="ml-auto text-xs text-emerald-700">{selected ? 'Steps below' : 'Show steps'}</span>
                </span>
                <Summary option={o} />
              </button>
              {selected && <Steps option={o} id={panelId} />}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
