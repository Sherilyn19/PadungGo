import { CircleAlert, RotateCcw, Sparkles } from 'lucide-react'
import { rideReferences, type JourneyOption, type TripSearch } from '../../api'
import { useTripExplanation } from '../../hooks/useTripExplanation'
import LoadingButton from '../ui/LoadingButton'

interface Props {
  option: JourneyOption
  // The search behind these results. Without it the server cannot find the trip.
  search: TripSearch | null
}

// Optional AI summary of the selected trip. Nothing is requested until the
// button is pressed, and the directions below never wait for it.
export default function TripExplanation({ option, search }: Props) {
  const { state, explain } = useTripExplanation(option, search)
  // Older backends do not send the ride IDs, so there is nothing to explain from.
  if (!search || !rideReferences(option)) return null

  return (
    <section className="space-y-2 border-b border-cream-line bg-white p-3" aria-label="Trip explanation">
      {(state.phase === 'idle' || state.phase === 'loading') && (
        <div className="space-y-2">
          <LoadingButton
            type="button"
            className="btn-primary w-full"
            loading={state.phase === 'loading'}
            loadingLabel="Explaining…"
            icon={<Sparkles size={17} aria-hidden="true" />}
            onClick={() => void explain()}
          >
            Explain this trip
          </LoadingButton>
          <p className="text-xs text-ink-muted" role="status" aria-live="polite">
            {state.phase === 'loading'
              ? 'Asking the AI. This can take a few seconds. Your directions below are ready to use.'
              : 'A short, plain-English summary written by AI from the trip details below.'}
          </p>
        </div>
      )}

      {state.phase === 'ready' && (
        <div className="fade-up space-y-2">
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="badge badge-blue">
              <Sparkles size={12} aria-hidden="true" />
              AI-generated
            </span>
            {state.model && <span className="text-[11px] break-all text-ink-soft">{state.model} · open-weight</span>}
          </p>
          <div className="space-y-1.5 text-sm leading-relaxed text-ink">
            {state.paragraphs.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </div>
          {state.notices.length > 0 && (
            <div className="rounded-[4px] border border-cream-line bg-caution-50 px-2.5 py-2 text-caution">
              <p className="text-xs font-semibold">Before you go</p>
              <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs">
                {state.notices.map((notice) => (
                  <li key={notice}>{notice}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-[11px] text-ink-soft">
            AI can make mistakes. The directions below come from the trip planner, not the AI.
          </p>
        </div>
      )}

      {state.phase === 'unavailable' && (
        <div className="fade-up space-y-2">
          <div className="flex items-start gap-2 rounded-[4px] border border-alert/40 bg-alert-50 p-2.5 text-sm text-ink" role="alert">
            <CircleAlert size={16} className="mt-0.5 shrink-0 text-alert" aria-hidden="true" />
            <div className="min-w-0">
              <p>{state.message}</p>
              <p className="mt-0.5 text-xs text-ink-muted">Your trip details below are not affected.</p>
            </div>
          </div>
          {state.retryable && (
            <button type="button" className="btn w-full" onClick={() => void explain()}>
              <RotateCcw size={16} aria-hidden="true" />
              Try again
            </button>
          )}
        </div>
      )}
    </section>
  )
}
