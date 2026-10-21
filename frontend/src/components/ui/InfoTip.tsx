import { Info } from 'lucide-react'
import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

interface Props {
  // Accessible name of the (i) button, e.g. "About the fare".
  label: string
  children: ReactNode
  className?: string
}

const GAP = 8
const EDGE = 8
const WIDTH = 260

interface Position {
  top: number
  left: number
  placement: 'top' | 'bottom'
}

// Small (i) button that reveals a longer explanation. The tooltip is rendered
// in a portal on <body> so cards, scroll areas and the map never clip it.
// Hover or focus opens it on desktop, tap toggles it on touch, Escape closes it.
export default function InfoTip({ label, children, className = '' }: Props) {
  const tipId = useId()
  const button = useRef<HTMLButtonElement>(null)
  const tip = useRef<HTMLDivElement>(null)
  const closeTimer = useRef<number | undefined>(undefined)
  const [open, setOpen] = useState(false)
  const [pinned, setPinned] = useState(false)
  const [pos, setPos] = useState<Position | null>(null)

  const show = useCallback(() => {
    window.clearTimeout(closeTimer.current)
    setOpen(true)
  }, [])
  const hideSoon = useCallback(() => {
    if (pinned) return
    window.clearTimeout(closeTimer.current)
    closeTimer.current = window.setTimeout(() => setOpen(false), 120)
  }, [pinned])
  const close = useCallback(() => {
    setOpen(false)
    setPinned(false)
  }, [])

  // Place above the icon, flip below when there is no room, and keep it on screen.
  const place = useCallback(() => {
    const anchor = button.current?.getBoundingClientRect()
    const box = tip.current?.getBoundingClientRect()
    if (!anchor || !box) return
    const width = Math.min(WIDTH, window.innerWidth - EDGE * 2)
    const left = Math.min(
      window.innerWidth - width - EDGE,
      Math.max(EDGE, anchor.left + anchor.width / 2 - width / 2),
    )
    const fitsAbove = anchor.top - box.height - GAP >= EDGE
    const top = fitsAbove ? anchor.top - box.height - GAP : anchor.bottom + GAP
    setPos({ top, left, placement: fitsAbove ? 'top' : 'bottom' })
  }, [])

  useLayoutEffect(() => {
    if (open) place()
    else setPos(null)
  }, [open, place])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        close()
        button.current?.focus()
      }
    }
    const onOutside = (e: PointerEvent) => {
      const target = e.target as Node
      if (!button.current?.contains(target) && !tip.current?.contains(target)) close()
    }
    // Scrolling moves the anchor, so follow it.
    window.addEventListener('scroll', place, true)
    window.addEventListener('resize', place)
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onOutside)
    return () => {
      window.removeEventListener('scroll', place, true)
      window.removeEventListener('resize', place)
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('pointerdown', onOutside)
    }
  }, [open, place, close])

  useEffect(() => () => window.clearTimeout(closeTimer.current), [])

  return (
    <>
      <button
        ref={button}
        type="button"
        aria-label={label}
        aria-describedby={open ? tipId : undefined}
        aria-expanded={open}
        className={`focus-ring inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-brand-500 transition-colors hover:bg-brand-100 hover:text-brand-700 ${className}`}
        onPointerEnter={(e) => e.pointerType === 'mouse' && show()}
        onPointerLeave={(e) => e.pointerType === 'mouse' && hideSoon()}
        onFocus={show}
        onBlur={() => !pinned && hideSoon()}
        onClick={(e) => {
          // Inside clickable cards: don't toggle the card as well.
          e.stopPropagation()
          if (pinned) close()
          else {
            setPinned(true)
            show()
          }
        }}
      >
        <Info size={15} strokeWidth={2.25} aria-hidden="true" />
      </button>
      {open &&
        createPortal(
          <div
            ref={tip}
            id={tipId}
            role="tooltip"
            onPointerEnter={show}
            onPointerLeave={hideSoon}
            style={{
              position: 'fixed',
              top: pos?.top ?? -9999,
              left: pos?.left ?? -9999,
              width: Math.min(WIDTH, window.innerWidth - EDGE * 2),
              transformOrigin: pos?.placement === 'bottom' ? 'top center' : 'bottom center',
              visibility: pos ? 'visible' : 'hidden',
            }}
            className="tip-in z-[1000] rounded-[4px] border border-brand-800 bg-white text-xs leading-relaxed text-ink shadow-[0_4px_14px_rgb(6_47_87/0.18)]"
          >
            <div className="titlebar flex h-6 items-center gap-1.5 rounded-t-[3px] px-2 font-pixel text-[11px] tracking-wide">
              <Info size={12} aria-hidden="true" />
              {label}
            </div>
            <div className="px-3 py-2">{children}</div>
          </div>,
          document.body,
        )}
    </>
  )
}
