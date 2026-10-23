import { useCallback, useEffect, useRef, useState } from 'react'
import { explainJourney, type JourneyOption, type TripSearch } from '../api'
import {
  explanationFromError,
  explanationFromResponse,
  IDLE,
  LOADING,
  type ExplanationState,
} from '../tripExplanation'

// Asks for an explanation only when `explain` is called (one click), never
// automatically. Callers key the component by trip, so a different trip starts
// again from idle; leaving the screen cancels a request that is still running.
export function useTripExplanation(option: JourneyOption, search: TripSearch | null) {
  const [state, setState] = useState<ExplanationState>(IDLE)
  const controller = useRef<AbortController | null>(null)

  useEffect(() => () => controller.current?.abort(), [])

  const explain = useCallback(async () => {
    if (!search || controller.current) return // already asking
    const request = new AbortController()
    controller.current = request
    setState(LOADING)
    try {
      const body = await explainJourney(search, option, request.signal)
      if (!request.signal.aborted) setState(explanationFromResponse(body))
    } catch (e) {
      if (!request.signal.aborted) setState(explanationFromError(e))
    } finally {
      if (controller.current === request) controller.current = null
    }
  }, [option, search])

  return { state, explain }
}
