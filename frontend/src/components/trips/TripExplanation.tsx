import { Bus, ChevronDown, CircleAlert, RotateCcw, Sparkles } from 'lucide-react'
import { useId, useState } from 'react'
import { rideReferences, type JourneyOption, type TripSearch } from '../../api'
import { useTripExplanation } from '../../hooks/useTripExplanation'
import { animatedParagraphs, shortModelName, showsOlderRecordsReminder } from '../../tripExplanation'

interface Props {
  option: JourneyOption
  // The search behind these results. Without it the server cannot find the trip.
  search: TripSearch | null
}

// Small stars that twinkle around the button. Positions and timings differ so
// they never blink in step.
const STARS = [
  { className: 'top-1.5 left-[12%]', delay: '0s' },
  { className: 'right-[14%] bottom-1.5', delay: '0.7s' },
  { className: 'top-2 right-[26%] scale-75', delay: '1.3s' },
  { className: 'bottom-2 left-[30%] scale-75', delay: '1.9s' },
]

function MagicButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="btn btn-primary btn-magic focus-ring w-full">
      {STARS.map((star) => (
        <span key={star.delay} className={`magic-star ${star.className}`} style={{ animationDelay: star.delay }} aria-hidden="true" />
      ))}
      <Sparkles size={19} className="magic-icon" aria-hidden="true" />
      Explain this trip
    </button>
  )
}

function Thinking() {
  return (
    <div className="summary-card space-y-2.5 rounded-[6px] border border-brand-200 bg-brand-50 p-3" role="status" aria-live="polite">
      <div className="flex items-center gap-2 text-brand-700">
        <Sparkles size={17} className="spin-slow shrink-0" aria-hidden="true" />
        <span className="font-pixel text-sm font-semibold tracking-wide">Cooking up a friendly summary</span>
        <span className="ml-0.5 flex gap-1" aria-hidden="true">
          {[0, 1, 2].map((d) => (
            <span key={d} className="hop-dot h-1.5 w-1.5 rounded-full bg-brand-500" style={{ ['--d' as string]: d }} />
          ))}
        </span>
      </div>
      <div className="space-y-1.5" aria-hidden="true">
        <div className="skeleton h-3 w-full rounded-full" />
        <div className="skeleton h-3 w-11/12 rounded-full" />
        <div className="skeleton h-3 w-2/3 rounded-full" />
      </div>
      <p className="text-xs text-ink-muted">Your directions below are ready to use while you wait.</p>
    </div>
  )
}

interface SummaryProps {
  paragraphs: string[]
  notices: string[]
  model: string
}

// The summary card. Its header is always visible, with the AI-generated label,
// and folds the text away with a smooth height transition.
function Summary({ paragraphs, notices, model }: SummaryProps) {
  const [open, setOpen] = useState(true)
  const bodyId = useId()
  const words = animatedParagraphs(paragraphs)
  const modelName = shortModelName(model)

  return (
    <div className="summary-card overflow-hidden rounded-[6px] border border-brand-200 bg-gradient-to-br from-brand-50 via-white to-cream shadow-[0_2px_0_rgb(186_217_243/0.8)]">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={bodyId}
        className="focus-ring flex w-full items-center gap-2.5 px-3 py-2.5 text-left transition-colors hover:bg-brand-50/70"
      >
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[5px] border border-brand-800 bg-brand-500 text-white shadow-[inset_0_1px_0_rgb(255_255_255/0.35)]">
          <Bus size={17} className={open ? 'magic-icon' : ''} aria-hidden="true" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-pixel text-base leading-tight font-semibold tracking-wide text-ink">Here&rsquo;s the gist!</span>
          <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="badge badge-blue" title={modelName ? `Written by ${model}, an open-weight AI model` : undefined}>
              <Sparkles size={12} aria-hidden="true" />
              AI-generated
            </span>
            <span className="text-xs text-ink-muted">{open ? 'Tap to tuck away' : 'Tap to open'}</span>
          </span>
        </span>
        <ChevronDown
          size={18}
          className={`shrink-0 text-brand-600 transition-transform duration-300 ease-out ${open ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      <div
        id={bodyId}
        data-open={open}
        // `inert` keeps folded-away text out of reach of keyboards and screen readers.
        inert={!open}
        className="grid grid-rows-[0fr] opacity-0 transition-[grid-template-rows,opacity] duration-300 ease-out data-[open=true]:grid-rows-[1fr] data-[open=true]:opacity-100"
      >
        <div className="min-h-0 overflow-hidden">
          <div className="space-y-2 border-t border-brand-100 px-3 pt-2.5 pb-3">
            <div className="space-y-1.5 text-[15px] leading-relaxed text-ink">
              {words.map((paragraph, index) => (
                <p key={index}>
                  {paragraph.map((word) => (
                    <span key={word.index} className="word-in" style={{ ['--w' as string]: word.index }}>
                      {word.text}
                      {'\u00a0'}
                    </span>
                  ))}
                </p>
              ))}
            </div>
            {showsOlderRecordsReminder(notices) && (
              <p className="flex items-start gap-1.5 rounded-[4px] bg-caution-50 px-2.5 py-1.5 text-xs text-caution">
                <Bus size={13} className="mt-px shrink-0" aria-hidden="true" />
                Routes come from older records, so look for the signboard before you hop on.
              </p>
            )}
            <p className="text-[11px] text-ink-soft">
              AI can make mistakes. Your steps below come from the trip planner{modelName ? ` · ${modelName}, open-weight` : ''}.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function Oops({ message, retryable, onRetry }: { message: string; retryable: boolean; onRetry: () => void }) {
  return (
    <div className="summary-card space-y-2">
      <div className="flex items-start gap-2.5 rounded-[6px] border border-alert/30 bg-alert-50 p-2.5 text-sm text-ink" role="alert">
        <CircleAlert size={18} className="oops-shake mt-0.5 shrink-0 text-alert" aria-hidden="true" />
        <div className="min-w-0">
          <p className="font-semibold">Hmm, I couldn&rsquo;t sum this one up.</p>
          <p className="mt-0.5 text-ink-muted">{message}</p>
          <p className="mt-0.5 text-xs text-ink-muted">Your trip details below are not affected.</p>
        </div>
      </div>
      {retryable && (
        <button type="button" className="btn focus-ring group w-full" onClick={onRetry}>
          <RotateCcw size={16} className="transition-transform duration-500 group-hover:-rotate-180" aria-hidden="true" />
          Try again
        </button>
      )}
    </div>
  )
}

// Optional AI summary of the selected trip. Nothing is requested until the
// button is pressed, and the directions below never wait for it.
export default function TripExplanation({ option, search }: Props) {
  const { state, explain } = useTripExplanation(option, search)
  // Older backends do not send the ride IDs, so there is nothing to explain from.
  if (!search || !rideReferences(option)) return null

  return (
    <section className="space-y-2 border-b border-cream-line bg-white p-3" aria-label="Trip explanation">
      {state.phase === 'idle' && (
        <div className="space-y-2">
          <MagicButton onClick={() => void explain()} />
          <p className="text-center text-xs text-ink-muted">Get a quick, friendly walkthrough of this ride.</p>
        </div>
      )}
      {state.phase === 'loading' && <Thinking />}
      {state.phase === 'ready' && <Summary paragraphs={state.paragraphs} notices={state.notices} model={state.model} />}
      {state.phase === 'unavailable' && <Oops message={state.message} retryable={state.retryable} onRetry={() => void explain()} />}
    </section>
  )
}
