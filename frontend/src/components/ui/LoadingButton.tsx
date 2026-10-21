import { LoaderCircle } from 'lucide-react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  loading: boolean
  icon: ReactNode
  loadingLabel: string
}

// Keeps its size and colour while busy: only the icon and label change, so
// nothing around it moves. Clicks are ignored while loading.
export default function LoadingButton({ loading, icon, loadingLabel, children, className = '', disabled, onClick, ...rest }: Props) {
  return (
    <button
      {...rest}
      aria-busy={loading}
      aria-disabled={disabled || loading}
      disabled={disabled && !loading}
      onClick={(e) => {
        if (loading) e.preventDefault()
        else onClick?.(e)
      }}
      className={`btn ${loading ? 'cursor-progress' : ''} ${className}`}
    >
      {loading ? <LoaderCircle size={17} className="animate-spin" aria-hidden="true" /> : icon}
      <span className="truncate">{loading ? loadingLabel : children}</span>
    </button>
  )
}
