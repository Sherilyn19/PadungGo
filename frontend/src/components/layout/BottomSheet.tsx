import { useEffect, useRef, useState, type PointerEvent, type ReactNode } from 'react'

export type SheetSnap = 'peek' | 'half' | 'full'

interface Props {
  snap: SheetSnap
  onSnapChange: (snap: SheetSnap) => void
  onHeightChange: (height: number) => void
  header: ReactNode
  children: ReactNode
}

const PEEK_PX = 148
// Leave a strip of map visible at the top even when fully open.
const FULL_GAP_PX = 64

function snapHeights(containerHeight: number): Record<SheetSnap, number> {
  return {
    peek: PEEK_PX,
    half: Math.round(containerHeight * 0.52),
    full: containerHeight - FULL_GAP_PX,
  }
}

// Phone layout: the planner lives in a draggable sheet over the map.
export default function BottomSheet({ snap, onSnapChange, onHeightChange, header, children }: Props) {
  const sheet = useRef<HTMLElement>(null)
  const [containerHeight, setContainerHeight] = useState(() => window.innerHeight)
  const [dragHeight, setDragHeight] = useState<number | null>(null)
  const drag = useRef<{ y: number; height: number; moved: boolean } | null>(null)

  useEffect(() => {
    const parent = sheet.current?.parentElement
    if (!parent) return
    const observer = new ResizeObserver(([entry]) => setContainerHeight(entry.contentRect.height))
    observer.observe(parent)
    return () => observer.disconnect()
  }, [])

  const heights = snapHeights(containerHeight)
  const height = dragHeight ?? heights[snap]

  useEffect(() => {
    if (dragHeight === null) onHeightChange(heights[snap])
  }, [snap, containerHeight, dragHeight])

  const onPointerDown = (e: PointerEvent<HTMLElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId)
    drag.current = { y: e.clientY, height, moved: false }
  }
  const onPointerMove = (e: PointerEvent<HTMLElement>) => {
    const start = drag.current
    if (!start) return
    const dy = start.y - e.clientY
    if (Math.abs(dy) > 4) start.moved = true
    if (start.moved) setDragHeight(Math.min(heights.full, Math.max(PEEK_PX, start.height + dy)))
  }
  const onPointerUp = () => {
    const start = drag.current
    drag.current = null
    if (!start) return
    if (!start.moved) {
      // A tap cycles peek → half → full → peek.
      onSnapChange(snap === 'peek' ? 'half' : snap === 'half' ? 'full' : 'peek')
      return
    }
    const current = dragHeight ?? height
    const nearest = (Object.keys(heights) as SheetSnap[]).reduce((best, key) =>
      Math.abs(heights[key] - current) < Math.abs(heights[best] - current) ? key : best,
    )
    setDragHeight(null)
    onSnapChange(nearest)
  }

  return (
    <section
      ref={sheet}
      aria-label="Trip planner"
      className={`absolute inset-x-0 bottom-0 z-20 flex flex-col overflow-hidden rounded-t-[8px] border-t border-brand-800 bg-white shadow-[0_-4px_18px_rgb(6_47_87/0.18)] ${
        dragHeight === null ? 'transition-[height] duration-300 ease-[cubic-bezier(0.2,0.8,0.2,1)]' : ''
      }`}
      style={{ height }}
    >
      <div
        className="relative shrink-0 touch-none select-none"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={() => {
          drag.current = null
          setDragHeight(null)
        }}
      >
        <button
          type="button"
          className="absolute top-1 left-1/2 z-10 flex h-4 w-16 -translate-x-1/2 items-center justify-center focus-visible:outline-2 focus-visible:outline-white"
          aria-label={snap === 'full' ? 'Collapse trip panel' : 'Expand trip panel'}
          aria-expanded={snap !== 'peek'}
          onClick={(e) => {
            // Keyboard activation; pointer taps are handled by the drag area.
            if (e.detail === 0) onSnapChange(snap === 'peek' ? 'half' : snap === 'half' ? 'full' : 'peek')
          }}
        >
          <span className="h-1 w-10 rounded-full bg-white/70" aria-hidden="true" />
        </button>
        {header}
      </div>
      <div className="bg-grid min-h-0 flex-1 overflow-y-auto overscroll-contain">{children}</div>
    </section>
  )
}
