import { useEffect, useState } from 'react'

const STARTUP_SCREEN_DURATION_MS = 5000

// Show the welcome screen once per page mount, independent of map/network speed.
export function useStartupReadiness() {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    const timeout = window.setTimeout(() => setReady(true), STARTUP_SCREEN_DURATION_MS)
    return () => window.clearTimeout(timeout)
  }, [])
  return { ready }
}
