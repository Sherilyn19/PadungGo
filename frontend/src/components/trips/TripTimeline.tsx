import {
  ArrowDownToDot,
  ArrowRightLeft,
  BusFront,
  CircleDot,
  Flag,
  Footprints,
  MoveDown,
  type LucideIcon,
} from 'lucide-react'
import type { CSSProperties, ReactNode } from 'react'
import { groupTimeline, rideColor, rideSoftColor, type TimelineKind, type TimelineStep } from '../../tripTimeline'
import RidePlate, { ScarceBadge } from './RidePlate'

const KIND: Record<TimelineKind, { label: string; icon: LucideIcon }> = {
  start: { label: 'Start', icon: CircleDot },
  walk: { label: 'Walk', icon: Footprints },
  board: { label: 'Board', icon: BusFront },
  ride: { label: 'Ride', icon: MoveDown },
  alight: { label: 'Get off', icon: ArrowDownToDot },
  transfer: { label: 'Transfer', icon: ArrowRightLeft },
  arrive: { label: 'Arrive', icon: Flag },
}

// Marker look per step. Ride steps take their ride's colour; walking stays grey
// with a dotted line, so rides and walks differ by shape as well as colour.
function markerStyle(step: TimelineStep): { className: string; style?: CSSProperties } {
  const base = 'relative z-10 flex h-8 w-8 shrink-0 items-center justify-center border-2'
  const color = step.rideIndex !== undefined ? rideColor(step.rideIndex) : undefined
  switch (step.kind) {
    case 'start':
      return { className: `${base} rounded-full border-brand-500 bg-white text-brand-600` }
    case 'walk':
      return { className: `${base} rounded-full border-dashed border-line-strong bg-white text-ink-muted` }
    case 'board':
      return { className: `${base} rounded-full border-white text-white shadow-[0_0_0_1px_rgb(0_0_0/0.15)]`, style: { backgroundColor: color } }
    case 'ride':
      return { className: `${base} rounded-[6px] bg-white`, style: { borderColor: color, color } }
    case 'alight':
      return { className: `${base} rounded-full bg-white`, style: { borderColor: color, color } }
    case 'transfer':
      return { className: `${base} rounded-[6px] border-white bg-brand-950 text-white shadow-[0_0_0_1px_rgb(6_47_87/0.4)]` }
    case 'arrive':
      return { className: `${base} rounded-full border-white bg-alert text-white shadow-[0_0_0_1px_rgb(232_17_35/0.4)]` }
  }
}

// One row: marker on the rail, text beside it. `line` is the connector drawn
// down to the next row.
function Row({ step, index, line }: { step: TimelineStep; index: number; line: 'solid' | 'dotted' | 'none' }) {
  const { label, icon: Icon } = KIND[step.kind]
  const marker = markerStyle(step)
  const color = step.rideIndex !== undefined ? rideColor(step.rideIndex) : undefined
  const labelColor = step.kind === 'arrive' ? 'text-alert' : step.kind === 'walk' ? 'text-ink-soft' : color ? '' : 'text-brand-600'
  return (
    <li className="timeline-step relative flex gap-3 pb-4 last:pb-0" style={{ '--i': index } as CSSProperties}>
      {line === 'solid' && (
        <span className="timeline-connector absolute top-8 -bottom-px left-[14px] w-1 rounded-full" style={{ backgroundColor: color }} aria-hidden="true" />
      )}
      {line === 'dotted' && (
        <span className="timeline-connector absolute top-9 bottom-1 left-[15px] w-0 border-l-2 border-dotted border-line-strong" aria-hidden="true" />
      )}
      <span className={marker.className} style={marker.style} aria-hidden="true">
        <Icon size={16} strokeWidth={2.25} />
      </span>
      <div className="min-w-0 flex-1 pt-0.5">
        <p className={`font-pixel text-[11px] font-semibold tracking-[0.08em] uppercase ${labelColor}`} style={color ? { color } : undefined}>
          {label}
        </p>
        <p className="text-sm leading-snug font-semibold break-words text-ink">{step.title}</p>
        {step.detail && <p className="mt-0.5 text-[13px] text-ink-muted">{step.detail}</p>}
      </div>
    </li>
  )
}

interface Props {
  steps: TimelineStep[]
  // Extra content at the bottom of each ride block (jeepney type and fare).
  rideFooter?: (rideIndex: number) => ReactNode
}

export default function TripTimeline({ steps, rideFooter }: Props) {
  const blocks = groupTimeline(steps)
  let index = 0
  return (
    <ol className="space-y-0" aria-label="Trip directions">
      {blocks.map((block, b) => {
        const isLast = b === blocks.length - 1
        if (block.type === 'step') {
          return <Row key={b} step={block.step} index={index++} line={isLast ? 'none' : 'dotted'} />
        }
        // A ride is one tinted block, so it is clear where it starts and ends.
        const color = rideColor(block.rideIndex)
        return (
          <li key={b} className="relative pb-4">
            {!isLast && (
              <span className="absolute -bottom-0 left-[15px] h-4 border-l-2 border-dotted border-line-strong" aria-hidden="true" />
            )}
            <div
              className="timeline-step -ml-2 rounded-[6px] py-2.5 pr-2.5 pl-2"
              style={{ backgroundColor: rideSoftColor(block.rideIndex), boxShadow: `inset 3px 0 0 ${color}`, '--i': index } as CSSProperties}
            >
              <div className="mb-2 ml-11 flex flex-wrap items-center gap-2">
                <span className="font-pixel text-[11px] font-bold tracking-[0.08em] uppercase" style={{ color }}>
                  Ride {block.rideIndex + 1}
                </span>
                <RidePlate code={block.routeCode} rideIndex={block.rideIndex} />
                {block.scarce && <ScarceBadge />}

                {block.routeName && <span className="w-full text-xs text-ink-soft">{block.routeName}</span>}
              </div>
              <ol>
                {block.steps.map((step, s) => (
                  <Row key={s} step={step} index={index++} line={s < block.steps.length - 1 ? 'solid' : 'none'} />
                ))}
              </ol>
              {rideFooter && <div className="mt-3 ml-11">{rideFooter(block.rideIndex)}</div>}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
