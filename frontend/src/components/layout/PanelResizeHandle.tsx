import { GripVertical } from 'lucide-react'
import type { ResizablePanelState } from '../../hooks/useResizablePanel'

interface Props {
  panel: ResizablePanelState
  controls: string
  label: string
}

// Draggable, keyboard-operable edge between a panel and what follows it.
export default function PanelResizeHandle({ panel, controls, label }: Props) {
  const { width, dragging, min, max, handleProps } = panel
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={`${label}. Use the arrow keys to resize, or press Enter to hide it.`}
      aria-controls={controls}
      aria-valuemin={min}
      aria-valuemax={max}
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
  )
}
