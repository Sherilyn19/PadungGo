import { useEffect, type Dispatch, type SetStateAction } from 'react'
import { lookUpAddress, type Place } from '../api'
import { labelIfStillCurrent } from '../places'

/**
 * Looks up a readable address for a GPS or map point that is still pending.
 * If the user moves the point (or clears it) before the reply arrives, the
 * old lookup is cancelled and its reply ignored.
 */
export function useAddressLabel(place: Place | null, setPlace: Dispatch<SetStateAction<Place | null>>) {
  useEffect(() => {
    if (!place || place.addressStatus !== 'pending') return
    const target = place
    const controller = new AbortController()
    lookUpAddress(target, controller.signal)
      .catch(() => null)
      .then((response) => {
        if (controller.signal.aborted) return
        setPlace((current) => labelIfStillCurrent(current, target, response))
      })
    return () => controller.abort()
  }, [place, setPlace])
}
