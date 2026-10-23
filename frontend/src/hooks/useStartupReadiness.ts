import { useCallback, useEffect, useState } from 'react'

// The map controls readiness; a network stall must not lock the trip planner.
export function useStartupReadiness() {
  const [ready, setReady] = useState(false)
  const markReady = useCallback(() => setReady(true), [])
  useEffect(() => {
    if (ready) return
    const timeout = window.setTimeout(markReady, 10000)
    return () => window.clearTimeout(timeout)
  }, [ready, markReady])
  return { ready, markReady }
}
