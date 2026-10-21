import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react'

export const SIDEBAR_MIN = 320
export const SIDEBAR_MAX = 640
export const SIDEBAR_DEFAULT = 400
const KEY_STEP = 24
const STORAGE_KEY = 'padunggo.sidebar'

interface Stored {
  width: number
  collapsed: boolean
}

// The panel never takes so much room that the map becomes unusable.
function maxWidth(): number {
  return Math.max(SIDEBAR_MIN, Math.min(SIDEBAR_MAX, window.innerWidth - 280))
}

export function clampWidth(width: number, max = SIDEBAR_MAX): number {
  return Math.round(Math.min(max, Math.max(SIDEBAR_MIN, width)))
}

function load(): Stored {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null') as Partial<Stored> | null
    return {
      width: typeof raw?.width === 'number' && Number.isFinite(raw.width) ? clampWidth(raw.width) : SIDEBAR_DEFAULT,
      collapsed: raw?.collapsed === true,
    }
  } catch {
    // Storage can be blocked (private mode); fall back to defaults.
    return { width: SIDEBAR_DEFAULT, collapsed: false }
  }
}

export function useResizableSidebar() {
  const [state, setState] = useState<Stored>(load)
  const [dragging, setDragging] = useState(false)
  const dragStart = useRef<{ x: number; width: number } | null>(null)
  const frame = useRef(0)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    } catch {
      /* Remembering the width is a convenience only. */
    }
  }, [state])

  // Keep the panel within limits when the window shrinks.
  useEffect(() => {
    const onResize = () => setState((s) => ({ ...s, width: clampWidth(s.width, maxWidth()) }))
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const setWidth = useCallback((width: number) => {
    setState((s) => ({ ...s, width: clampWidth(width, maxWidth()) }))
  }, [])

  const toggleCollapsed = useCallback(() => setState((s) => ({ ...s, collapsed: !s.collapsed })), [])

  const onPointerDown = useCallback(
    (e: PointerEvent<HTMLElement>) => {
      if (e.button !== 0) return
      e.preventDefault()
      e.currentTarget.setPointerCapture(e.pointerId)
      dragStart.current = { x: e.clientX, width: state.width }
      setDragging(true)
    },
    [state.width],
  )

  const onPointerMove = useCallback(
    (e: PointerEvent<HTMLElement>) => {
      const start = dragStart.current
      if (!start) return
      const next = start.width + (e.clientX - start.x)
      // One state update per frame keeps dragging smooth.
      cancelAnimationFrame(frame.current)
      frame.current = requestAnimationFrame(() => setWidth(next))
    },
    [setWidth],
  )

  const endDrag = useCallback(() => {
    dragStart.current = null
    setDragging(false)
  }, [])

  const onKeyDown = useCallback(
    (e: KeyboardEvent<HTMLElement>) => {
      const actions: Record<string, () => void> = {
        ArrowLeft: () => setWidth(state.width - KEY_STEP),
        ArrowRight: () => setWidth(state.width + KEY_STEP),
        Home: () => setWidth(SIDEBAR_MIN),
        End: () => setWidth(maxWidth()),
        Enter: toggleCollapsed,
      }
      const action = actions[e.key]
      if (action) {
        e.preventDefault()
        action()
      }
    },
    [setWidth, state.width, toggleCollapsed],
  )

  // While dragging, keep the resize cursor everywhere and stop text selection.
  useEffect(() => {
    if (!dragging) return
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    return () => {
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [dragging])

  return {
    width: state.width,
    collapsed: state.collapsed,
    dragging,
    toggleCollapsed,
    resetWidth: () => setWidth(SIDEBAR_DEFAULT),
    handleProps: {
      onPointerDown,
      onPointerMove,
      onPointerUp: endDrag,
      onPointerCancel: endDrag,
      onKeyDown,
      onDoubleClick: () => setWidth(SIDEBAR_DEFAULT),
    },
  }
}
