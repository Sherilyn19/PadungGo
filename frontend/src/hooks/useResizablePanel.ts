import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react'

const KEY_STEP = 24
// The map always keeps at least this much room beside the panels.
const MIN_MAP_WIDTH = 280

export interface PanelLimits {
  storageKey: string
  min: number
  max: number
  defaultWidth: number
  // Room already taken by other panels, so this one never squeezes the map.
  reservedWidth?: number
  // Remember collapsed state across visits (main panel), or not (trip details).
  persistCollapsed?: boolean
}

interface Stored {
  width: number
  collapsed: boolean
}

export function clampWidth(width: number, min: number, max: number): number {
  return Math.round(Math.min(max, Math.max(min, width)))
}

function load({ storageKey, min, max, defaultWidth, persistCollapsed }: PanelLimits): Stored {
  try {
    const raw = JSON.parse(localStorage.getItem(storageKey) ?? 'null') as Partial<Stored> | null
    return {
      width: typeof raw?.width === 'number' && Number.isFinite(raw.width) ? clampWidth(raw.width, min, max) : defaultWidth,
      collapsed: persistCollapsed === true && raw?.collapsed === true,
    }
  } catch {
    // Storage can be blocked (private mode); fall back to defaults.
    return { width: defaultWidth, collapsed: false }
  }
}

// Width, collapse state and drag/keyboard handlers for a side panel.
export function useResizablePanel(limits: PanelLimits) {
  const { storageKey, min, max, defaultWidth, reservedWidth = 0 } = limits
  const [state, setState] = useState<Stored>(() => load(limits))
  const [dragging, setDragging] = useState(false)
  const dragStart = useRef<{ x: number; width: number } | null>(null)
  const frame = useRef(0)

  const maxNow = useCallback(
    () => Math.max(min, Math.min(max, window.innerWidth - reservedWidth - MIN_MAP_WIDTH)),
    [min, max, reservedWidth],
  )

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(limits.persistCollapsed ? state : { width: state.width }))
    } catch {
      /* Remembering the width is a convenience only. */
    }
  }, [state, storageKey, limits.persistCollapsed])

  // Stay within limits when the window shrinks or another panel grows.
  useEffect(() => {
    const fit = () => setState((s) => ({ ...s, width: clampWidth(s.width, min, maxNow()) }))
    fit()
    window.addEventListener('resize', fit)
    return () => window.removeEventListener('resize', fit)
  }, [min, maxNow])

  const setWidth = useCallback((width: number) => setState((s) => ({ ...s, width: clampWidth(width, min, maxNow()) })), [min, maxNow])
  const setCollapsed = useCallback((collapsed: boolean) => setState((s) => ({ ...s, collapsed })), [])
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
        Home: () => setWidth(min),
        End: () => setWidth(maxNow()),
        Enter: toggleCollapsed,
      }
      const action = actions[e.key]
      if (action) {
        e.preventDefault()
        action()
      }
    },
    [setWidth, state.width, toggleCollapsed, min, maxNow],
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
    min,
    max,
    setCollapsed,
    toggleCollapsed,
    handleProps: {
      onPointerDown,
      onPointerMove,
      onPointerUp: endDrag,
      onPointerCancel: endDrag,
      onKeyDown,
      onDoubleClick: () => setWidth(defaultWidth),
    },
  }
}

export type ResizablePanelState = ReturnType<typeof useResizablePanel>
