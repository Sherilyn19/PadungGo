import { useEffect, useId, useRef, useState } from 'react'
import { searchLocations, type LocationResult, type Place } from '../api'

interface Props {
  label: string
  value: Place | null
  onChange: (place: Place | null) => void
  picking: boolean
  onPickOnMap: () => void
}

export default function PlaceInput({ label, value, onChange, picking, onPickOnMap }: Props) {
  const inputId = useId()
  const listId = useId()
  const [text, setText] = useState('')
  const [results, setResults] = useState<LocationResult[]>([])
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useState<string>('')
  const debounce = useRef<number | undefined>(undefined)

  useEffect(() => {
    setText(value?.name ?? '')
  }, [value])

  useEffect(() => {
    const q = text.trim()
    if (!open || q.length < 2 || q === value?.name) {
      setResults([])
      setStatus((s) => (s === 'Searching…' ? '' : s))
      return
    }
    const controller = new AbortController()
    window.clearTimeout(debounce.current)
    debounce.current = window.setTimeout(async () => {
      setStatus('Searching…')
      try {
        const data = await searchLocations(q, controller.signal)
        setResults(data.results)
        setStatus(data.results.length ? '' : 'No matching place. Try a street name, or pick on the map.')
      } catch (e) {
        if (!controller.signal.aborted) setStatus((e as Error).message)
      }
    }, 300)
    return () => controller.abort()
  }, [text, open, value?.name])

  const choose = (r: LocationResult) => {
    onChange({ id: r.id, name: r.name, latitude: r.latitude, longitude: r.longitude, source: 'search' })
    setOpen(false)
    setResults([])
  }

  const useGps = () => {
    if (!('geolocation' in navigator)) {
      setStatus('Location is not available in this browser. Search or pick on the map instead.')
      return
    }
    setStatus('Getting your location…')
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setStatus('')
        onChange({
          name: 'My location',
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          source: 'gps',
        })
      },
      () => setStatus('Location permission was denied. Search or pick on the map instead.'),
      { enableHighAccuracy: true, timeout: 15000 },
    )
  }

  return (
    <div className="relative">
      <label htmlFor={inputId} className="block text-sm font-medium text-slate-700">
        {label}
      </label>
      <div className="mt-1 flex gap-2">
        <input
          id={inputId}
          role="combobox"
          aria-expanded={open && results.length > 0}
          aria-controls={listId}
          aria-autocomplete="list"
          className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-200"
          placeholder="Search a street or landmark"
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            setOpen(true)
            if (value) onChange(null)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        />
        <button
          type="button"
          onClick={useGps}
          className="rounded-lg border border-slate-300 px-2 text-sm hover:bg-slate-50"
          title="Use my location"
          aria-label={`Use my location for ${label.toLowerCase()}`}
        >
          📍
        </button>
        <button
          type="button"
          onClick={onPickOnMap}
          aria-pressed={picking}
          className={`rounded-lg border px-2 text-sm ${picking ? 'border-emerald-600 bg-emerald-50 text-emerald-800' : 'border-slate-300 hover:bg-slate-50'}`}
          title="Pick on the map"
          aria-label={`Pick ${label.toLowerCase()} on the map`}
        >
          🗺️
        </button>
      </div>
      {open && results.length > 0 && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-slate-200 bg-white shadow-lg"
        >
          {results.map((r) => (
            <li key={r.id} role="option" aria-selected={false}>
              <button
                type="button"
                className="w-full px-3 py-2 text-left text-sm hover:bg-emerald-50"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => choose(r)}
              >
                {r.name}
              </button>
            </li>
          ))}
        </ul>
      )}
      {picking && <p className="mt-1 text-xs text-emerald-700">Tap the map to set this point.</p>}
      {status && (
        <p className="mt-1 text-xs text-slate-500" aria-live="polite">
          {status}
        </p>
      )}
    </div>
  )
}
