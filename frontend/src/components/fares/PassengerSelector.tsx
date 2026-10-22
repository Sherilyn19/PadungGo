import { Accessibility, GraduationCap, HandHeart, User } from 'lucide-react'
import type { ReactNode } from 'react'
import { PASSENGER_TYPES, type PassengerType } from '../../fareEstimates'
import SegmentedControl from '../ui/SegmentedControl'

const ICONS: Record<PassengerType, ReactNode> = {
  regular: <User size={14} aria-hidden="true" />,
  // One small icon per group, so all three stay recognisable at a glance.
  discounted: (
    <span className="inline-flex items-center gap-0.5" aria-hidden="true">
      <GraduationCap size={14} />
      <HandHeart size={14} />
      <Accessibility size={14} />
    </span>
  ),
}

// One passenger type for the whole trip. Student, senior and PWD pay the same
// discounted fare in both guides, so they share one choice. Icons appear once
// the panel is wide enough, so the labels never get squeezed on phones.
export default function PassengerSelector({ value, onChange }: { value: PassengerType; onChange: (value: PassengerType) => void }) {
  return (
    <div className="@container">
      <p className="mb-1.5 text-xs font-semibold text-ink-muted" aria-hidden="true">
        Passenger
      </p>
      <SegmentedControl
        label="Passenger type"
        value={value}
        onChange={onChange}
        accent="var(--color-moss-600)"
        className="grid-cols-[minmax(0,2fr)_minmax(0,3fr)] [&_svg]:hidden @[22rem]:[&_svg]:block"
        options={PASSENGER_TYPES.map((p) => ({ ...p, icon: ICONS[p.value] }))}
      />
    </div>
  )
}
