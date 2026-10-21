import { GripVertical } from 'lucide-react'
import type { ReactNode } from 'react'
import { SIDEBAR_MAX, SIDEBAR_MIN, type useResizableSidebar } from '../../hooks/useResizableSidebar'

interface Props {
  sidebar: ReturnType<typeof useResizableSidebar>
  children: ReactNode
}

// Resizable, collapsible left panel for tablets and desktops.
export default function DesktopSidebar({ sidebar, children }: Props) {
  const { width, collapsed, dragging, handleProps } = sidebar
  return (
    <>
      <aside
        id="trip-panel"
        aria-label="Trip planner"
        inert={collapsed}
        className={`relative h-full shrink-0 overflow-hidden border-brand-900/20 bg-white ${collapsed ? '' : 'border-r'} ${
          dragging ? '' : 'transition-[width] duration-300 ease-[cubic-bezier(0.2,0.8,0.2,1)]'
        }`}
        style={{ width: collapsed ? 0 : width }}
      >
        {/* Fixed inner width: collapsing slides the panel away instead of squeezing the text. */}
        <div className="flex h-full flex-col" style={{ width }}>
          {children}
        </div>
      </aside>
      {!collapsed && (
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize trip panel. Use the arrow keys, or press Enter to hide it."
          aria-controls="trip-panel"
          aria-valuemin={SIDEBAR_MIN}
          aria-valuemax={SIDEBAR_MAX}
          aria-valuenow={width}
          tabIndex={0}
          title="Drag to resize · double-click to reset"
          {...handleProps}
          className={`group relative z-20 -ml-px flex w-2 shrink-0 cursor-col-resize touch-none items-center justify-center transition-colors focus:outline-none focus-visible:bg-brand-200 ${
            dragging ? 'bg-brand-300' : 'bg-transparent hover:bg-brand-100'
          }`}
        >
          <span
            className={`flex h-10 w-3 items-center justify-center rounded-[3px] border bg-white transition-colors ${
              dragging ? 'border-brand-500 text-brand-600' : 'border-line-strong text-ink-soft group-hover:border-brand-400 group-hover:text-brand-600'
            }`}
            aria-hidden="true"
          >
            <GripVertical size={12} />
          </span>
        </div>
      )}
    </>
  )
}
