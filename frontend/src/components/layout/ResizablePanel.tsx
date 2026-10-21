import type { CSSProperties, ReactNode } from 'react'
import type { ResizablePanelState } from '../../hooks/useResizablePanel'
import PanelResizeHandle from './PanelResizeHandle'

interface Props {
  id: string
  label: string
  panel: ResizablePanelState
  // Hidden panels slide to zero width; `open` lets the caller close it too.
  open?: boolean
  className?: string
  style?: CSSProperties
  children: ReactNode
}

// Side panel that slides open and closed and can be resized from its right edge.
export default function ResizablePanel({ id, label, panel, open = true, className = '', style, children }: Props) {
  const { width, collapsed, dragging } = panel
  const visible = open && !collapsed
  return (
    <>
      <aside
        id={id}
        aria-label={label}
        inert={!visible}
        className={`relative h-full shrink-0 overflow-hidden bg-white ${visible ? '' : 'border-0!'} ${
          dragging ? '' : 'transition-[width] duration-300 ease-[cubic-bezier(0.2,0.8,0.2,1)]'
        } ${className}`}
        style={{ ...style, width: visible ? width : 0 }}
      >
        {/* Fixed inner width: closing slides the panel away instead of squeezing the text. */}
        <div className="flex h-full flex-col" style={{ width }}>
          {children}
        </div>
      </aside>
      {visible && <PanelResizeHandle panel={panel} controls={id} label={`Resize ${label.toLowerCase()}`} />}
    </>
  )
}
