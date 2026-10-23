import { LoaderCircle, LocateFixed, MapPin, MousePointerClick, X } from 'lucide-react'
import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import { suggestPlaces, type Attribution, type Place, type PlaceSuggestion } from '../../api'
import {
  ADDRESS_PRIVACY_NOTE,
  cachedSuggestions,
  formatCoordinates,
  pendingPoint,
  placeFromSuggestion,
  rememberSuggestions,
  suggestionAttribution,
  suggestionKey,
} from '../../places'

interface Props {
  label: string
  placeholder: string
  value: Place | null
  onChange: (place: Place | null) => void
  picking: boolean
  onPickOnMap: () => void
}

export default function PlaceInput({ label, placeholder, value, onChange, picking, onPickOnMap }: Props) {
  const inputId = useId()
  const listId = useId()
  const [text, setText] = useState('')
  const [results, setResults] = useState<PlaceSuggestion[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)
  const debounce = useRef<number | undefined>(undefined)
  // Set when typing clears the selection, so that clear doesn't also wipe the typed text.
  const clearedByTyping = useRef(false)
  const lower = label.toLowerCase()

  useEffect(() => {
    if (clearedByTyping.current) {
      clearedByTyping.current = false
      return
    }
    setText(value?.name ?? '')
  }, [value])

  useEffect(() => {
    const q = text.trim()
    if (!open || q.length < 2 || q === value?.name) {
      setResults([])
      setBusy(false)
      return
    }
    const showResults = (found: PlaceSuggestion[]) => {
      setResults(found)
      setActive(-1)
      setStatus(found.length ? '' : 'No matching place. Try a street name, or pick it on the map.')
    }
    const cached = cachedSuggestions(q)
    if (cached) {
      showResults(cached.results)
      return
    }
    const controller = new AbortController()
    window.clearTimeout(debounce.current)
    debounce.current = window.setTimeout(async () => {
      setBusy(true)
      try {
        const data = await suggestPlaces(q, controller.signal)
        if (controller.signal.aborted) return
        rememberSuggestions(q, data)
        showResults(data.results)
      } catch (e) {
        if (!controller.signal.aborted) setStatus((e as Error).message)
      } finally {
        if (!controller.signal.aborted) setBusy(false)
      }
    }, 300)
    return () => {
      window.clearTimeout(debounce.current)
      controller.abort()
    }
  }, [text, open, value?.name])

  const choose = (r: PlaceSuggestion) => {
    onChange(placeFromSuggestion(r))
    setOpen(false)
    setResults([])
    setStatus('')
  }

  const clear = () => {
    setText('')
    setResults([])
    setStatus('')
    onChange(null)
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
        onChange(pendingPoint(pos.coords, 'gps'))
      },
      (err) => setStatus(gpsErrorMessage(err)),
      { enableHighAccuracy: true, timeout: 15000 },
    )
  }

  const listOpen = open && results.length > 0
  const listCredits = suggestionAttribution(results)

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!listOpen) return
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      const step = e.key === 'ArrowDown' ? 1 : -1
      setActive((i) => (i + step + results.length) % results.length)
    } else if (e.key === 'Enter' && active >= 0) {
      e.preventDefault()
      choose(results[active])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div className="relative min-w-0 flex-1">
      <label htmlFor={inputId} className="mb-1 block text-[11px] font-semibold tracking-wide text-ink-soft uppercase">
        {label}
      </label>
      <div className="flex gap-1.5">
        <div className="relative min-w-0 flex-1">
          <input
            id={inputId}
            role="combobox"
            aria-expanded={listOpen}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={listOpen && active >= 0 ? `${listId}-${active}` : undefined}
            autoComplete="off"
            className="field pr-8 pl-3"
            placeholder={placeholder}
            value={text}
            onChange={(e) => {
              setText(e.target.value)
              setOpen(true)
              setStatus('')
              if (value) {
                clearedByTyping.current = true
                onChange(null)
              }
            }}
            onKeyDown={onKeyDown}
            onFocus={() => setOpen(true)}
            onBlur={() => window.setTimeout(() => setOpen(false), 150)}
          />
          <span className="absolute inset-y-0 right-1 flex items-center">
            {busy ? (
              <LoaderCircle size={16} className="mr-1.5 animate-spin text-brand-500" aria-label="Searching" />
            ) : text ? (
              <button
                type="button"
                onClick={clear}
                className="focus-ring flex h-7 w-7 items-center justify-center rounded-[3px] text-ink-soft hover:bg-brand-50 hover:text-brand-700"
                aria-label={`Clear ${lower}`}
              >
                <X size={15} aria-hidden="true" />
              </button>
            ) : null}
          </span>
        </div>
        <button type="button" onClick={useGps} className="icon-btn" title="Use my location" aria-label={`Use my location for ${lower}`}>
          <LocateFixed size={18} aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={onPickOnMap}
          aria-pressed={picking}
          className="icon-btn"
          title="Pick on the map"
          aria-label={`Pick ${lower} on the map`}
        >
          <MousePointerClick size={18} aria-hidden="true" />
        </button>
      </div>
      {listOpen && (
        <div className="fade-up absolute z-30 mt-1 w-full overflow-hidden rounded-[4px] border border-brand-800 bg-white shadow-[0_6px_16px_rgb(6_47_87/0.16)]">
          <ul
            id={listId}
            role="listbox"
            aria-label={`${label} suggestions`}
            className="max-h-72 overflow-auto py-1"
          >
            {results.map((r, i) => (
              <li
                key={suggestionKey(r)}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === active}
                className={`flex cursor-pointer items-start gap-2 px-3 py-2 text-sm ${i === active ? 'bg-brand-500 text-white' : 'hover:bg-brand-50'}`}
                onMouseDown={(e) => e.preventDefault()}
                onMouseEnter={() => setActive(i)}
                onClick={() => choose(r)}
              >
                <MapPin size={15} className={`mt-0.5 shrink-0 ${i === active ? 'text-white' : 'text-brand-500'}`} aria-hidden="true" />
                <span className="min-w-0">
                  <span className="block truncate font-medium">{r.name}</span>
                  {(r.detail || r.source === 'geoapify') && (
                    <span className={`block truncate text-xs ${i === active ? 'text-brand-100' : 'text-ink-soft'}`}>
                      {/* Map-data results are places, not PadungGo route evidence. */}
                      {[r.detail, r.source === 'geoapify' ? 'Map result' : null].filter(Boolean).join(' · ')}
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ul>
          {listCredits.length > 0 && (
            <p className="border-t border-brand-100 px-3 py-1 text-[11px] text-ink-soft" onMouseDown={(e) => e.preventDefault()}>
              <Credits items={listCredits} />
            </p>
          )}
        </div>
      )}
      <PointCaption place={value} />
      {status && (
        <p className="mt-1 text-xs text-ink-muted" aria-live="polite">
          {status}
        </p>
      )}
    </div>
  )
}

function gpsErrorMessage(err: GeolocationPositionError): string {
  if (err.code === err.PERMISSION_DENIED) return 'Location permission was denied. Search or pick on the map instead.'
  if (err.code === err.TIMEOUT) return 'Finding your location took too long. Try again, or pick on the map.'
  return 'Your location is not available right now. Search or pick on the map instead.'
}

function Credits({ items }: { items: Attribution[] }) {
  return (
    <>
      {items.map((c, i) => (
        <span key={c.text}>
          {i > 0 && ' · '}
          {c.url ? (
            <a href={c.url} target="_blank" rel="noopener noreferrer" className="underline hover:text-brand-700">
              {c.text}
            </a>
          ) : (
            c.text
          )}
        </span>
      ))}
    </>
  )
}

// Shows the exact coordinates of a GPS or map point, the lookup's privacy note,
// and the credits required wherever a Geoapify result is shown.
function PointCaption({ place }: { place: Place | null }) {
  if (!place) return null
  const isPoint = place.source === 'gps' || place.source === 'map'
  if (!isPoint && !place.attribution?.length) return null
  return (
    <div className="mt-1 space-y-0.5 text-[11px] text-ink-soft" aria-live="polite">
      {isPoint && (
        <p>
          {place.addressStatus === 'pending' ? 'Finding the address… ' : ''}
          <span className="tabular-nums">{formatCoordinates(place)}</span>
        </p>
      )}
      {isPoint && <p>{ADDRESS_PRIVACY_NOTE}</p>}
      {place.attribution?.length ? (
        <p>
          <Credits items={place.attribution} />
        </p>
      ) : null}
    </div>
  )
}
