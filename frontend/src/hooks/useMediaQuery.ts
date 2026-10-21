import { useSyncExternalStore } from 'react'

export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const list = window.matchMedia(query)
      list.addEventListener('change', onChange)
      return () => list.removeEventListener('change', onChange)
    },
    () => window.matchMedia(query).matches,
    () => false,
  )
}

// Matches Tailwind's `md` breakpoint: tablets and desktops get the sidebar,
// phones get the bottom sheet.
export const DESKTOP_QUERY = '(min-width: 768px)'
