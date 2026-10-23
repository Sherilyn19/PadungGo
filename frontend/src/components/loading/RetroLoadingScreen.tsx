import { BusFront, Heart } from 'lucide-react'
import { useEffect, useState, type CSSProperties } from 'react'
import './retro-loading-screen.css'

export default function RetroLoadingScreen({ ready }: { ready: boolean }) {
  const [dismissed, setDismissed] = useState(false)
  useEffect(() => {
    if (!ready) return
    const timer = window.setTimeout(() => setDismissed(true), 650)
    return () => window.clearTimeout(timer)
  }, [ready])
  if (dismissed) return null

  return (
    <div className={`retro-loading-screen${ready ? ' retro-loading-screen--leaving' : ''}`} aria-hidden={ready || undefined}>
      <section className="retro-loading-window" role="status" aria-live="polite" aria-label="Loading PadungGo">
        <div className="retro-loading-titlebar" aria-hidden="true">
          <span><BusFront size={15} /> PadungGo.exe</span>
          <span className="retro-loading-window-controls">− □ ♡</span>
        </div>
        <div className="retro-loading-content">
          <div className="retro-loading-stamp" aria-hidden="true"><BusFront size={32} strokeWidth={1.7} /><Heart size={12} /></div>
          <p className="retro-loading-heading">A tiny pause before we go.</p>
          <div className="retro-loading-dots" aria-hidden="true">
            {Array.from({ length: 5 }, (_, index) => (
              <span key={index} style={{ '--dot-index': index } as CSSProperties} />
            ))}
          </div>
          <p className="retro-loading-phrase">Take a breath. Let’s go somewhere.</p>
          <p className="retro-loading-caption">Opening your little window to Cebu…</p>
        </div>
        <div className="retro-loading-status" aria-hidden="true"><span>MAP.EXE</span><span>{ready ? 'Ready to wander!' : 'Warming up the journey…'}</span></div>
      </section>
    </div>
  )
}
