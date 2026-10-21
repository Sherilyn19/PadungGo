import { PanelLeftClose, Route } from 'lucide-react'

interface Props {
  onCollapse?: () => void
}

// Blue "window" title bar with the PadungGo mark.
export default function PanelHeader({ onCollapse }: Props) {
  return (
    <header className="titlebar flex h-14 shrink-0 items-center gap-2.5 px-3">
      <span className="flex h-8 w-8 items-center justify-center rounded-[4px] border border-brand-900 bg-white text-brand-600 shadow-[inset_0_-2px_0_rgb(0_66_122/0.15)]">
        <Route size={18} strokeWidth={2.5} aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <h1 className="font-pixel text-xl leading-none font-bold tracking-wide">PadungGo</h1>
        <p className="mt-0.5 truncate text-[11px] text-brand-100">Jeepney trips in Metro Cebu</p>
      </div>
      {onCollapse && (
        <button
          type="button"
          onClick={onCollapse}
          className="flex h-8 w-8 items-center justify-center rounded-[3px] border border-brand-900/60 bg-white/10 text-white transition-colors hover:bg-white/25 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          aria-label="Hide trip panel"
          title="Hide panel"
        >
          <PanelLeftClose size={17} aria-hidden="true" />
        </button>
      )}
    </header>
  )
}
