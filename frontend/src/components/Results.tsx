import type { JourneyOption, PlanResponse, RideSegment } from '../api'
import { explainReason, formatDistance, formatDuration, formatFare, titleCase } from '../format'

interface Props {
  plan: PlanResponse
  selectedId: string | null
  onSelect: (id: string) => void
}

const LABELS: Record<string, string> = {
  fewest_transfers: 'Fewest transfers',
  cheapest: 'Cheapest',
  fastest: 'Fastest',
}

function rides(o: JourneyOption): RideSegment[] {
  return o.segments.filter((s): s is RideSegment => s.mode === 'ride')
}

export default function Results({ plan, selectedId, onSelect }: Props) {
  if (plan.journey_options.length === 0) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="status">
        <p className="font-semibold">No journey found</p>
        <p className="mt-1">{explainReason(plan.reason)}</p>
        <p className="mt-1 text-xs">This does not prove that no jeepney serves this trip — only that the current data has none.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {plan.ranking.warning && <p className="text-xs text-slate-600">{plan.ranking.warning}</p>}
      <ol className="space-y-3">
        {plan.journey_options.map((o, i) => {
          const selected = o.id === selectedId
          const documented = o.evidence.verification_status !== 'verified'
          return (
            <li key={o.id}>
              <button
                type="button"
                onClick={() => onSelect(o.id)}
                aria-pressed={selected}
                className={`w-full rounded-lg border p-3 text-left transition ${selected ? 'border-emerald-600 bg-emerald-50 ring-2 ring-emerald-200' : 'border-slate-200 bg-white hover:border-slate-300'}`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-slate-900">Option {i + 1}</span>
                  {rides(o).map((r, k) => (
                    <span key={k} className="rounded bg-slate-900 px-1.5 py-0.5 font-mono text-xs text-white">
                      {r.route_code}
                    </span>
                  ))}
                  <span className="text-xs text-slate-600">
                    {o.transfers === 0 ? 'Direct' : '1 transfer'}
                  </span>
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
                </div>

                <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <dt className="text-slate-500">Fare</dt>
                    <dd className="font-medium">
                      {o.fare.total_is_complete ? formatFare(o.fare.total_centavos) : 'Unknown'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Riding</dt>
                    <dd className="font-medium">
                      {formatDuration(o.time.riding_seconds)}
                      {o.time.riding_seconds !== null && <span className="text-slate-500"> (schedule)</span>}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Waiting · walking</dt>
                    <dd className="font-medium">Unknown</dd>
                  </div>
                </dl>

                {selected && (
                  <ol className="mt-3 space-y-2 border-t border-slate-200 pt-3 text-sm">
                    {o.segments.map((s, k) => (
                      <li key={k} className="flex gap-2">
                        <span aria-hidden="true">{s.mode === 'ride' ? '🚐' : '🚶'}</span>
                        <div>
                          {s.mode === 'ride' ? (
                            <>
                              <p>
                                Ride <strong>{s.route_code}</strong>
                                {s.route_name && <> — {titleCase(s.route_name)}</>}
                              </p>
                              <p className="text-xs text-slate-600">
                                Board at <strong>{s.board_stop_name}</strong>, get off at{' '}
                                <strong>{s.alight_stop_name}</strong>
                              </p>
                              <p className="text-xs text-slate-500">
                                {formatDistance(s.distance_m)} on the road ·{' '}
                                {formatDuration(s.duration_seconds)} riding · fare{' '}
                                {formatFare(s.fare.amount_centavos)}
                                {s.signboard && <> · signboard “{s.signboard}”</>}
                              </p>
                            </>
                          ) : s.mode === 'transfer_walk' ? (
                            <p className="text-xs text-slate-700">{s.instruction} Path not verified.</p>
                          ) : (
                            <p className="text-xs text-slate-700">
                              {s.instruction.replace(' (approximate; not a verified route).', '')}{' '}
                              <span className="text-slate-500">
                                (~{formatDistance(s.straight_line_m)} straight line; check the actual street path)
                              </span>
                            </p>
                          )}
                        </div>
                      </li>
                    ))}
                    {o.warnings.map((w) => (
                      <li key={w} className="text-xs text-amber-800">⚠ {w}</li>
                    ))}
                    {o.evidence.references.map((ref, k) =>
                      ref.title ? (
                        <li key={`ref-${k}`} className="text-xs text-slate-500">
                          Source: {ref.title}
                          {ref.publisher && <> ({ref.publisher})</>}
                        </li>
                      ) : null,
                    )}
                  </ol>
                )}
              </button>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
