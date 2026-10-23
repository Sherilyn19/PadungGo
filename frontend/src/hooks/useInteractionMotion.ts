import { useEffect, useRef } from 'react'

// One delegated listener; animations run outside React and stop when finished.
export function useInteractionMotion() {
  const root = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const element = root.current
    if (!element) return
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
    const active = new Set<Animation>()
    const ripples = new Set<HTMLElement>()
    const clear = () => {
      active.forEach((animation) => animation.cancel())
      ripples.forEach((ripple) => ripple.remove())
      active.clear()
      ripples.clear()
    }
    const click = (event: MouseEvent) => {
      if (preference.matches || !(event.target instanceof Element)) return
      const button = event.target.closest<HTMLButtonElement>('button.btn, button.icon-btn, button.segmented-option')
      if (!button || button.disabled || !element.contains(button) || !button.animate) return
      // Keep rapid clicks bounded, even on slower devices.
      clear()
      const rect = button.getBoundingClientRect()
      const ripple = document.createElement('span')
      ripple.className = 'button-ripple'
      ripple.setAttribute('aria-hidden', 'true')
      const size = Math.hypot(rect.width, rect.height) * 2
      Object.assign(ripple.style, {
        width: `${size}px`, height: `${size}px`,
        left: `${(event.detail === 0 ? rect.width / 2 : event.clientX - rect.left) - size / 2}px`,
        top: `${(event.detail === 0 ? rect.height / 2 : event.clientY - rect.top) - size / 2}px`,
      })
      button.append(ripple)
      ripples.add(ripple)
      const animation = ripple.animate([
        { transform: 'scale(0)', opacity: 0.32 },
        { transform: 'scale(1)', opacity: 0 },
      ], { duration: 520, easing: 'cubic-bezier(0.16, 1, 0.3, 1)' })
      active.add(animation)
      animation.onfinish = () => {
        ripple.remove()
        ripples.delete(ripple)
        active.delete(animation)
      }
    }
    element.addEventListener('click', click)
    preference.addEventListener('change', clear)
    return () => {
      element.removeEventListener('click', click)
      preference.removeEventListener('change', clear)
      clear()
    }
  }, [])
  return root
}
