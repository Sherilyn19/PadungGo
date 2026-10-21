import { ArrowDownToDot, ArrowRightLeft, Banknote, BusFront, CircleDot, Flag, Footprints, type LucideIcon } from 'lucide-react'
import type { CSSProperties } from 'react'
import type { TimelineKind, TimelineStep } from '../../tripTimeline'
import InfoTip from '../ui/InfoTip'
import FareText from './FareText'

const KIND_LABEL: Record<TimelineKind, string> = {
  start: 'Start',
  walk: 'Walk',
  board: 'Board',
  alight: 'Get off',
  transfer: 'Transfer',
  arrive: 'Arrive',
}

const KIND_ICON: Record<TimelineKind, LucideIcon> = {
  start: CircleDot,
  walk: Footprints,
  board: BusFront,
  alight: ArrowDownToDot,
  transfer: ArrowRightLeft,
  arrive: Flag,
}

function Marker({ step }: { step: TimelineStep }) {
  const Icon = KIND_ICON[step.kind]
  const base = 'relative z-10 flex h-8 w-8 items-center justify-center border-2'
  const styles: Record<TimelineKind, { className: string; style?: CSSProperties }> = {
    start: { className: `${base} rounded-full border-brand-500 bg-white text-brand-600` },
    walk: { className: `${base} rounded-full border-line-strong bg-white text-ink-muted` },
    board: { className: `${base} rounded-full border-white text-white shadow-[0_0_0_1px_rgb(6_47_87/0.35)]`, style: { backgroundColor: step.color } },
    alight: { className: `${base} rounded-full bg-white`, style: { borderColor: step.color, color: step.color } },
    transfer: { className: `${base} rounded-[5px] border-white bg-brand-950 text-white shadow-[0_0_0_1px_rgb(6_47_87/0.5)]` },
    arrive: { className: `${base} rounded-full border-white bg-alert text-white shadow-[0_0_0_1px_rgb(232_17_35/0.5)]` },
  }
  const { className, style } = styles[step.kind]
  return (
    <span className={className} style={style} aria-hidden="true">
      <Icon size={16} strokeWidth={2.25} />
    </span>
  )
}

function Connector({ step, index }: { step: TimelineStep; index: number }) {
  if (step.connector === 'none') return null
  const style = { '--i': index } as CSSProperties
  return step.connector === 'ride' ? (
    <span
      className="timeline-connector absolute top-8 bottom-0 left-[14px] w-1 rounded-full"
      style={{ ...style, backgroundColor: step.color }}
      aria-hidden="true"
    />
  ) : (
    <span
      className="timeline-connector absolute top-9 bottom-1 left-[15px] w-0 border-l-2 border-dotted border-line-strong"
      style={style}
      aria-hidden="true"
    />
  )
}

function StepBody({ step }: { step: TimelineStep }) {
  const labelColor =
    step.kind === 'arrive' ? 'text-alert' : step.kind === 'walk' ? 'text-ink-soft' : 'text-brand-600'
  return (
    <div
      className={`min-w-0 flex-1 pb-5 ${
        step.kind === 'transfer'
          ? 'mb-3 rounded-[4px] border border-dashed border-brand-400 bg-brand-50 px-2.5 pt-1.5 pb-2'
          : step.kind === 'arrive'
            ? 'rounded-[4px] border border-alert/30 bg-alert-50 px-2.5 pt-1.5 pb-2'
            : 'pt-0.5'
      }`}
    >
      <p className={`font-pixel text-[11px] font-semibold tracking-[0.08em] uppercase ${labelColor}`}>{KIND_LABEL[step.kind]}</p>
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm leading-snug font-semibold text-ink">
        {step.routeCode && (
          <span className="route-plate" style={{ backgroundColor: step.color }}>
            <BusFront size={13} aria-hidden="true" />
            {step.routeCode}
          </span>
        )}
        <span className="break-words">{step.title}</span>
      </p>
      {step.routeName && <p className="mt-0.5 text-xs text-ink-soft">{step.routeName}</p>}
      {step.detail && (
        <p className="mt-1 flex items-center gap-1 text-[13px] text-ink-muted">
          {step.detail}
          {!step.note && step.info && <InfoTip label={`About this ${KIND_LABEL[step.kind].toLowerCase()} step`}>{step.info}</InfoTip>}
        </p>
      )}
      {step.note && (
        <p className="mt-0.5 flex items-center gap-1 text-xs text-ink-soft">
          {step.note}
          {step.info && <InfoTip label={`About this ${KIND_LABEL[step.kind].toLowerCase()} step`}>{step.info}</InfoTip>}
        </p>
      )}
      {step.fare && (
        <p className="mt-1.5 flex items-center gap-1.5 text-xs text-ink-muted">
          <Banknote size={14} className="text-brand-500" aria-hidden="true" />
          <span className="sr-only">Fare:</span>
          <FareText fare={step.fare} />
        </p>
      )}
    </div>
  )
}

export default function TripTimeline({ steps }: { steps: TimelineStep[] }) {
  return (
    <ol className="relative" aria-label="Trip directions">
      {steps.map((step, index) => (
        <li key={index} className="timeline-step relative flex gap-3" style={{ '--i': index } as CSSProperties}>
          <Connector step={step} index={index} />
          <Marker step={step} />
          <StepBody step={step} />
        </li>
      ))}
    </ol>
  )
}
